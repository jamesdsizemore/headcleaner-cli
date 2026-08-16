# Homebrew formula for headcleaner.
#
# This is the canonical formula content. To use it:
#   1. Create a repo: local/homebrew-headcleaner (a Homebrew tap)
#   2. Put this file at Formula/headcleaner.rb in that repo
#   3. Users install via: brew install local/headcleaner/headcleaner
#
# Verify the SHA256 against the release artifact before publishing.

class Headcleaner < Formula
  desc "Walk a folder, convert every document to Markdown and/or OKF v0.2"
  homepage "https://github.com/local/headcleaner"
  url "https://github.com/local/headcleaner/archive/refs/tags/v0.4.0.tar.gz"
  sha256 "REPLACE_WITH_RELEASE_SHA256"
  license "Apache-2.0"

  depends_on "node" => :optional  # for OfficeCLI engine (Office formats)
  depends_on "python@3.12"

  # uv is the recommended installer; brew installs uv as a build-time dep
  resource "uv" do
    url "https://github.com/astral-sh/uv/releases/download/0.4.18/uv-x86_64-apple-darwin.tar.gz"
    sha256 "REPLACE_WITH_UV_SHA256"
  end

  def install
    resource("uv").stage do
      bin.install "uv" => "uv"
    end
    (buildpath/"bin").install_symlink libexec/"uv"

    # Build a wheel into lib/ and install it
    system "uv", "build", "--wheel", "--out-dir", libexec
    wheel = Dir[libexec/"*.whl"].first
    system "uv", "pip", "install", "--python", "python3.12", "--prefix", libexec, wheel
  end

  def post_install
    # Install OfficeCLI engine if the user opted in
    return unless which("npm")
    system "npm", "install", "-g", "@officecli/officecli"
  end

  test do
    system bin/"headcleaner", "--version"
  end
end
