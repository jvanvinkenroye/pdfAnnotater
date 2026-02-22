# Homebrew formula for PDF Annotator
#
# Installation:
#   brew tap jvanvinkenroye/pdf-annotator
#   brew install pdf-annotator

class PdfAnnotator < Formula
  include Language::Python::Virtualenv

  desc "PDF annotation tool with side-by-side view for notes"
  homepage "https://github.com/jvanvinkenroye/pdfAnnotater"
  url "https://github.com/jvanvinkenroye/pdfAnnotater/archive/refs/tags/v0.3.0.tar.gz"
  sha256 "4a7309c02bb0cef7ea7fb063919bcf8ac5cd1612442359cf3ac52ddf403444eb"
  license "MIT"
  head "https://github.com/jvanvinkenroye/pdfAnnotater.git", branch: "main"

  depends_on "python@3.12"

  resource "Flask" do
    url "https://files.pythonhosted.org/packages/dc/6d/cfe3c0fcc5e477df242b98bfe186a4c34357b4847e87ecaef04507332dab/flask-3.1.2.tar.gz"
    sha256 "bf656c15c80190ed628ad08cdfd3aaa35beb087855e2f494910aa3774cc4fd87"
  end

  resource "Werkzeug" do
    url "https://files.pythonhosted.org/packages/5a/70/1469ef1d3542ae7c2c7b72bd5e3a4e6ee69d7978fa8a3af05a38eca5becf/werkzeug-3.1.5.tar.gz"
    sha256 "6a548b0e88955dd07ccb25539d7d0cc97417ee9e179677d22c7041c8f078ce67"
  end

  resource "Jinja2" do
    url "https://files.pythonhosted.org/packages/df/bf/f7da0350254c0ed7c72f3e33cef02e048281fec7ecec5f032d4aac52226b/jinja2-3.1.6.tar.gz"
    sha256 "0137fb05990d35f1275a587e9aee6d56da821fc83491a0fb838183be43f66d6d"
  end

  resource "MarkupSafe" do
    url "https://files.pythonhosted.org/packages/7e/99/7690b6d4034fffd95959cbe0c02de8deb3098cc577c67bb6a24fe5d7caa7/markupsafe-3.0.3.tar.gz"
    sha256 "722695808f4b6457b320fdc131280796bdceb04ab50fe1795cd540799ebe1698"
  end

  resource "itsdangerous" do
    url "https://files.pythonhosted.org/packages/9c/cb/8ac0172223afbccb63986cc25049b154ecfb5e85932587206f42317be31d/itsdangerous-2.2.0.tar.gz"
    sha256 "e0050c0b7da1eea53ffaf149c0cfbb5c6e2e2b69c4bef22c81fa6eb73e5f6173"
  end

  resource "click" do
    url "https://files.pythonhosted.org/packages/3d/fa/656b739db8587d7b5dfa22e22ed02566950fbfbcdc20311993483657a5c0/click-8.3.1.tar.gz"
    sha256 "12ff4785d337a1bb490bb7e9c2b1ee5da3112e94a8622f26a6c77f5d2fc6842a"
  end

  resource "blinker" do
    url "https://files.pythonhosted.org/packages/21/28/9b3f50ce0e048515135495f198351908d99540d69bfdc8c1d15b73dc55ce/blinker-1.9.0.tar.gz"
    sha256 "b4ce2265a7abece45e7cc896e98dbebe6cead56bcf805a3d23136d145f5445bf"
  end

  resource "PyMuPDF" do
    url "https://files.pythonhosted.org/packages/48/d6/09b28f027b510838559f7748807192149c419b30cb90e6d5f0cf916dc9dc/pymupdf-1.26.7.tar.gz"
    sha256 "71add8bdc8eb1aaa207c69a13400693f06ad9b927bea976f5d5ab9df0bb489c3"
  end

  resource "pillow" do
    url "https://files.pythonhosted.org/packages/d0/02/d52c733a2452ef1ffcc123b68e6606d07276b0e358db70eabad7e40042b7/pillow-12.1.0.tar.gz"
    sha256 "5c5ae0a06e9ea030ab786b0251b32c7e4ce10e58d983c0d5c56029455180b5b9"
  end

  resource "flaskwebgui" do
    url "https://files.pythonhosted.org/packages/ba/3b/6a81bb31370deb3a92a9cd36c3b2f83827b3cb126815a3414c39f1a70002/flaskwebgui-1.1.9.tar.gz"
    sha256 "3a5dfea6bb58479beced817cb3c7adeffba7f4965273c1cb00f728aeb9566ce1"
  end

  resource "psutil" do
    url "https://files.pythonhosted.org/packages/73/cb/09e5184fb5fc0358d110fc3ca7f6b1d033800734d34cac10f4136cfac10e/psutil-7.2.1.tar.gz"
    sha256 "f7583aec590485b43ca601dd9cea0dcd65bd7bb21d30ef4ddbf4ea6b5ed1bdd3"
  end

  # flask-wtf and its dependencies
  resource "flask-wtf" do
    url "https://files.pythonhosted.org/packages/80/9b/f1cd6e41bbf874f3436368f2c7ee3216c1e82d666ff90d1d800e20eb1317/flask_wtf-1.2.2.tar.gz"
    sha256 "79d2ee1e436cf570bccb7d916533fa18757a2f18c290accffab1b9a0b684666b"
  end

  resource "WTForms" do
    url "https://files.pythonhosted.org/packages/01/e4/633d080897e769ed5712dcfad626e55dbd6cf45db0ff4d9884315c6a82da/wtforms-3.2.1.tar.gz"
    sha256 "df3e6b70f3192e92623128123ec8dca3067df9cfadd43d59681e210cfb8d4682"
  end

  # flask-limiter and its dependencies
  resource "flask-limiter" do
    url "https://files.pythonhosted.org/packages/4e/98/71780be5d1afb941219c4b48d241d4e246e3062b017caa4e79c4dc71314c/flask_limiter-4.1.1.tar.gz"
    sha256 "ca11608fc7eec43dcea606964ca07c3bd4ec1ae89043a0f67f717899a4f48106"
  end

  resource "limits" do
    url "https://files.pythonhosted.org/packages/71/69/826a5d1f45426c68d8f6539f8d275c0e4fcaa57f0c017ec3100986558a41/limits-5.8.0.tar.gz"
    sha256 "c9e0d74aed837e8f6f50d1fcebcf5fd8130957287206bc3799adaee5092655da"
  end

  resource "ordered-set" do
    url "https://files.pythonhosted.org/packages/4c/ca/bfac8bc689799bcca4157e0e0ced07e70ce125193fc2e166d2e685b7e2fe/ordered-set-4.1.0.tar.gz"
    sha256 "694a8e44c87657c59292ede72891eb91d34131f6531463aab3009191c77364a8"
  end

  resource "deprecated" do
    url "https://files.pythonhosted.org/packages/49/85/12f0a49a7c4ffb70572b6c2ef13c90c88fd190debda93b23f026b25f9634/deprecated-1.3.1.tar.gz"
    sha256 "b1b50e0ff0c1fddaa5708a2c6b0a6588bb09b892825ab2b214ac9ea9d92a5223"
  end

  resource "wrapt" do
    url "https://files.pythonhosted.org/packages/f7/37/ae31f40bec90de2f88d9597d0b5281e23ffe85b893a47ca5d9c05c63a4f6/wrapt-2.1.1.tar.gz"
    sha256 "5fdcb09bf6db023d88f312bd0767594b414655d58090fc1c46b3414415f67fac"
  end

  resource "packaging" do
    url "https://files.pythonhosted.org/packages/a1/d4/1fc4078c65507b51b96ca8f8c3ba19e6a61c8253c72794544580a7b6c24d/packaging-25.0.tar.gz"
    sha256 "d443872c98d677bf60f6a1f2f8c1cb748e8fe762d2bf9d3148b5599295b0fc4f"
  end

  resource "typing-extensions" do
    url "https://files.pythonhosted.org/packages/72/94/1a15dd82efb362ac84269196e94cf00f187f7ed21c242792a923cdb1c61f/typing_extensions-4.15.0.tar.gz"
    sha256 "0cea48d173cc12fa28ecabc3b837ea3cf6f38c6d1136f85cbaaf598984861466"
  end

  def install
    virtualenv_install_with_resources
    bin.install_symlink libexec/"bin/pdf-annotator"
  end

  def caveats
    <<~EOS
      PDF Annotator speichert Daten in:
        ~/Library/Application Support/PDF-Annotator/

      Starten:
        pdf-annotator
    EOS
  end

  test do
    assert_match "pdf_annotator", shell_output("#{bin}/pdf-annotator --help 2>&1", 1)
  end
end
