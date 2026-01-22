# Homebrew formula for PDF Annotator
# Install: brew install --build-from-source ./homebrew/pdf-annotator.rb
# Or add to a tap for easier distribution

class PdfAnnotator < Formula
  include Language::Python::Virtualenv

  desc "PDF annotation tool with side-by-side view for notes"
  homepage "https://github.com/yourusername/pdfAnnotater"
  license "MIT"
  head "https://github.com/yourusername/pdfAnnotater.git", branch: "main"

  # For local installation, use:
  # url "file:///Users/java/src_own/pdfAnnotater"
  # Or for released versions:
  # url "https://github.com/yourusername/pdfAnnotater/archive/refs/tags/v0.1.0.tar.gz"
  # sha256 "YOUR_SHA256_HERE"

  depends_on "python@3.12"

  resource "flask" do
    url "https://files.pythonhosted.org/packages/af/47/93213ee66ef8fae3b93b3e29206f6b251e65c97bd91d8e1c5596ef15af0a/flask-3.1.0.tar.gz"
    sha256 "5f873c5184c897c8d9d1b05df1e3d01b14910ce69607a117bd3277098a5c8c3a"
  end

  resource "werkzeug" do
    url "https://files.pythonhosted.org/packages/9e/54/f87c185bc38d7167a1e6a9a0b9ef89258e2a44f9f3f2f9f1a8b5e1e2e4d8/werkzeug-3.1.3.tar.gz"
    sha256 "60723ce945c19328679571c9c73fc7a2dddd1d6e0f0a174f9a5b9a4efc18c24a"
  end

  resource "pymupdf" do
    url "https://files.pythonhosted.org/packages/source/P/PyMuPDF/PyMuPDF-1.24.0.tar.gz"
    sha256 "PLACEHOLDER_SHA256"
  end

  resource "pillow" do
    url "https://files.pythonhosted.org/packages/source/p/pillow/pillow-10.4.0.tar.gz"
    sha256 "PLACEHOLDER_SHA256"
  end

  resource "flaskwebgui" do
    url "https://files.pythonhosted.org/packages/source/f/flaskwebgui/flaskwebgui-1.1.9.tar.gz"
    sha256 "PLACEHOLDER_SHA256"
  end

  resource "psutil" do
    url "https://files.pythonhosted.org/packages/source/p/psutil/psutil-7.2.1.tar.gz"
    sha256 "PLACEHOLDER_SHA256"
  end

  def install
    virtualenv_install_with_resources

    # Create wrapper script
    (bin/"pdf-annotator").write <<~EOS
      #!/bin/bash
      exec "#{libexec}/bin/python" -c "from pdf_annotator.desktop import main; main()" "$@"
    EOS
  end

  def post_install
    # Create data directory
    (var/"pdf-annotator").mkpath
  end

  def caveats
    <<~EOS
      PDF Annotator stores data in:
        ~/Library/Application Support/PDF-Annotator/

      To start the application:
        pdf-annotator

      Or run in development mode:
        FLASK_ENV=development pdf-annotator
    EOS
  end

  test do
    system "#{bin}/pdf-annotator", "--help"
  end
end
