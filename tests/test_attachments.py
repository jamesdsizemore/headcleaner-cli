from __future__ import annotations

import io
import stat
import warnings
import zipfile
from email.message import EmailMessage
from hashlib import sha256

import pytest
from click.testing import CliRunner

from headcleaner.attachments import (
    AttachmentIdentity,
    AttachmentLimits,
    expand_archive_payload,
)
from headcleaner.cli import cli
from headcleaner.engines.eml import EmlAdapter
from headcleaner.engines.msg import MsgAdapter
from headcleaner.engines.pst import _msg_to_concept_dict
from headcleaner.policy import AttachmentLimits as PolicyAttachmentLimits


def test_attachment_limits_are_immutable_and_reject_non_positive_values() -> None:
    assert AttachmentLimits is PolicyAttachmentLimits
    limits = AttachmentLimits(max_depth=2, max_members=4, max_member_bytes=100, max_total_bytes=300)

    assert limits.max_total_bytes == 300
    with pytest.raises(AttributeError):
        limits.max_depth = 3  # type: ignore[misc]
    with pytest.raises(ValueError, match="max_members"):
        AttachmentLimits(max_depth=1, max_members=0, max_member_bytes=1, max_total_bytes=1)


def test_attachment_identity_uses_logical_uri_and_safe_ordinal_path() -> None:
    payload = b"safe attachment"
    identity = AttachmentIdentity.from_payload(
        parent_source_sha256="a" * 64,
        parent_attachment_id="mail-part-1",
        child_ordinal=2,
        original_filename="../../unsafe.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        payload=payload,
    )

    assert identity.source_uri == "attachment:" + "a" * 64 + "/mail-part-1/2"
    assert identity.extracted_sha256 == sha256(payload).hexdigest()
    assert identity.output_stem == "a" * 16 + "-0002"


def test_eml_adapter_exposes_attachment_payload_lineage(tmp_path) -> None:
    source = tmp_path / "message.eml"
    source.write_bytes(
        b"From: sender@example.test\n"
        b"Subject: Attachment test\n"
        b"MIME-Version: 1.0\n"
        b'Content-Type: multipart/mixed; boundary="BOUNDARY"\n\n'
        b"--BOUNDARY\nContent-Type: text/plain\n\nBody\n"
        b"--BOUNDARY\nContent-Type: text/plain\n"
        b'Content-Disposition: attachment; filename="unsafe/../report.txt"\n\n'
        b"attached contents\n--BOUNDARY--\n"
    )

    out = EmlAdapter().extract(source)

    assert out["attachments"] == [
        {
            "attachment_id": "eml-part-0",
            "parent_source_sha256": sha256(source.read_bytes()).hexdigest(),
            "parent_attachment_id": "eml-part-0",
            "child_ordinal": 0,
            "filename": "unsafe/../report.txt",
            "media_type": "text/plain",
            "payload": b"attached contents",
            "source_uri": f"attachment:{sha256(source.read_bytes()).hexdigest()}/eml-part-0/0",
            "sha256": sha256(b"attached contents").hexdigest(),
        }
    ]


def test_eml_attachment_limits_quarantine_oversize_member_and_keep_sibling(tmp_path) -> None:
    source = tmp_path / "limited.eml"
    source.write_bytes(
        b"MIME-Version: 1.0\nContent-Type: multipart/mixed; boundary=BOUNDARY\n\n"
        b"--BOUNDARY\nContent-Type: text/plain\n\nBody\n"
        b"--BOUNDARY\nContent-Type: text/plain\n"
        b"Content-Disposition: attachment; filename=ok.txt\n\nOK\n"
        b"--BOUNDARY\nContent-Type: text/plain\n"
        b"Content-Disposition: attachment; filename=large.txt\n\nTOO-LARGE\n"
        b"--BOUNDARY--\n"
    )

    out = EmlAdapter(
        attachment_limits=AttachmentLimits(
            max_depth=1, max_members=2, max_member_bytes=4, max_total_bytes=8
        )
    ).extract(source)

    assert [item["filename"] for item in out["attachments"]] == ["ok.txt"]
    assert out["attachment_diagnostics"] == [
        {"code": "ATTACHMENT_QUARANTINED", "reason": "max_member_bytes", "ordinal": 1}
    ]


def _zip_payload(entries: list[tuple[str | zipfile.ZipInfo, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for member, payload in entries:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr(member, payload)
    return buffer.getvalue()


def _parent_attachment(payload: bytes) -> dict:
    return {
        "attachment_id": "eml-part-0",
        "child_ordinal": 0,
        "filename": "bundle.zip",
        "media_type": "application/zip",
        "payload": payload,
        "source_uri": "attachment:" + "a" * 64 + "/eml-part-0/0",
        "sha256": sha256(payload).hexdigest(),
    }


def test_archive_expansion_rejects_traversal_and_keeps_safe_sibling() -> None:
    payload = _zip_payload([("../escape.txt", b"unsafe"), ("safe.txt", b"safe")])

    children, diagnostics = expand_archive_payload(
        _parent_attachment(payload), AttachmentLimits(), depth=1
    )

    assert [child["filename"] for child in children] == ["safe.txt"]
    assert children[0]["payload"] == b"safe"
    assert diagnostics == [
        {
            "code": "ATTACHMENT_QUARANTINED",
            "reason": "path_traversal",
            "ordinal": 0,
            "evidence": {"member": "../escape.txt"},
        }
    ]


def test_archive_expansion_rejects_symlink_duplicate_and_unsafe_xml() -> None:
    symlink = zipfile.ZipInfo("link.txt")
    symlink.create_system = 3
    symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
    payload = _zip_payload(
        [
            (symlink, b"target.txt"),
            ("same.txt", b"first"),
            ("same.txt", b"second"),
            ("unsafe.xml", b'<!DOCTYPE x [<!ENTITY secret "value">]><x>&secret;</x>'),
        ]
    )

    children, diagnostics = expand_archive_payload(
        _parent_attachment(payload), AttachmentLimits(), depth=1
    )

    assert [child["filename"] for child in children] == ["same.txt"]
    assert [item["reason"] for item in diagnostics] == [
        "symlink",
        "duplicate_member_id",
        "unsafe_xml",
    ]


def test_archive_expansion_rejects_encrypted_member_metadata_only() -> None:
    payload = bytearray(_zip_payload([("secret.txt", b"secret")]))
    local_header = payload.index(b"PK\x03\x04")
    central_header = payload.index(b"PK\x01\x02")
    payload[local_header + 6 : local_header + 8] = (1).to_bytes(2, "little")
    payload[central_header + 8 : central_header + 10] = (1).to_bytes(2, "little")

    children, diagnostics = expand_archive_payload(
        _parent_attachment(bytes(payload)), AttachmentLimits(), depth=1
    )

    assert children == []
    assert diagnostics[0]["reason"] == "encrypted"


def test_archive_expansion_enforces_depth_and_total_byte_boundaries() -> None:
    payload = _zip_payload([("one.txt", b"1234"), ("two.txt", b"5678")])
    limits = AttachmentLimits(
        max_depth=1,
        max_members=3,
        max_member_bytes=4,
        max_total_bytes=6,
    )

    children, diagnostics = expand_archive_payload(_parent_attachment(payload), limits, depth=1)
    too_deep_children, too_deep_diagnostics = expand_archive_payload(
        _parent_attachment(payload), limits, depth=2
    )

    assert [child["filename"] for child in children] == ["one.txt"]
    assert [item["reason"] for item in diagnostics] == ["max_total_bytes"]
    assert too_deep_children == []
    assert too_deep_diagnostics[0]["reason"] == "max_depth"


def test_pst_message_exposes_attachment_payload_lineage(tmp_path) -> None:
    message = EmailMessage()
    message["Subject"] = "PST lineage"
    message.set_content("Body")
    message.add_attachment(b"child", maintype="text", subtype="plain", filename="../child.txt")
    source = tmp_path / "mail.pst"
    source.write_bytes(b"pst-root")

    extracted = _msg_to_concept_dict(message, source, 1)

    attachment = extracted["attachments"][0]
    assert attachment["filename"] == "../child.txt"
    assert attachment["payload"] == b"child"
    assert attachment["parent_source_sha256"] == sha256(source.read_bytes()).hexdigest()
    assert attachment["source_uri"].startswith("attachment:")


def test_msg_adapter_exposes_attachment_payload_lineage(tmp_path, monkeypatch) -> None:
    import headcleaner.engines.msg as msg_module

    class FakeAttachment:
        longFilename = "../../child.txt"
        shortFilename = None
        data = b"msg-child"
        mimetype = "text/plain"

    class FakeMessage:
        subject = "MSG lineage"
        sender = "sender@example.test"
        to = "receiver@example.test"
        cc = ""
        date = None
        body = "Body"
        attachments = [FakeAttachment()]

    class FakeExtractMsg:
        @staticmethod
        def Message(_path):
            return FakeMessage()

    monkeypatch.setattr(msg_module, "HAS_EXTRACT_MSG", True)
    monkeypatch.setattr(msg_module, "extract_msg", FakeExtractMsg)
    source = tmp_path / "mail.msg"
    source.write_bytes(b"msg-root")

    extracted = MsgAdapter().extract(source)

    attachment = extracted["attachments"][0]
    assert attachment["filename"] == "../../child.txt"
    assert attachment["payload"] == b"msg-child"
    assert attachment["parent_source_sha256"] == sha256(source.read_bytes()).hexdigest()
    assert attachment["source_uri"].startswith("attachment:")


def test_convert_help_exposes_central_attachment_limits() -> None:
    result = CliRunner().invoke(cli, ["convert", "--help"])

    assert result.exit_code == 0
    assert "--attachment-max-depth" in result.output
    assert "--attachment-max-members" in result.output
    assert "--attachment-max-member-bytes" in result.output
    assert "--attachment-max-total-bytes" in result.output
