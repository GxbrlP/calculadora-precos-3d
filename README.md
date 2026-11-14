# Calculadora 3D

Aplicativo de desktop (Python + PySide6) que lê projetos fatiados do Bambu Studio
e calcula o custo e o preço de venda de uma impressão 3D: filamento, energia,
taxa de falha, mão de obra, embalagem e margens (varejo, atacado e revenda).
Os valores ficam em um banco SQLite local; nada é enviado para a internet.

## Baixar

Baixe a versão mais recente em
**[Releases](https://github.com/GxbrlP/calculadora-precos-3d/releases/latest)**.
Não precisa instalar Python nem nada além do arquivo.

**Windows** — baixe `Calculadora3D-X.Y.Z-windows.exe` e abra. Na primeira vez
o Windows pode mostrar **"O Windows protegeu o computador"** (SmartScreen):
clique em **Mais informações** e depois em **Executar assim mesmo**. O aviso
aparece porque o programa não tem assinatura digital paga, não por haver algo
errado com ele.

**Linux** — baixe `Calculadora3D-X.Y.Z-x86_64.AppImage`, dê permissão de
execução e abra:

```
chmod +x Calculadora3D-*-x86_64.AppImage
./Calculadora3D-*-x86_64.AppImage
```

(ou, no gerenciador de arquivos: Propriedades → Permissões → "Permitir executar
como programa"). Funciona em distribuições de 2022 em diante (Ubuntu 22.04+,
Fedora 36+, Mint 21+).

## Arquivo de entrada

O app espera o `.gcode.3mf` exportado do Bambu Studio com **Ctrl+G** (Exportar
G-code fatiado). Cada arquivo é um produto; para um produto de várias placas,
exporte no Bambu Studio um único `.gcode.3mf` com todas as placas fatiadas.

Um projeto salvo com **Ctrl+S** não serve para ler peso e tempo: o Bambu Studio
descarta o fatiamento ao salvar. Nesse caso o app avisa e pede o peso e o tempo
de impressão manualmente.

## Instalação

```
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Com uv: `uv venv && uv pip install -e ".[dev]"`. Requer Python 3.12 ou superior.

## Executar

```
python -m calculadora3d
```

## Testes

```
pytest
```

## Onde ficam os dados

- Windows: `%APPDATA%\Calculadora3D\dados.db`
- Linux: `~/.local/share/calculadora3d/dados.db` (ou
  `$XDG_DATA_HOME/calculadora3d/dados.db`)

Para fazer backup ou migrar de máquina, copie esse arquivo.

## Gerar os executáveis à mão

Normalmente não é preciso: as releases são geradas pelo GitHub Actions (veja
abaixo). Para gerar localmente, com o ambiente acima instalado
(`pip install -e ".[dev]"` já inclui o PyInstaller):

- **Windows:** `pyinstaller calculadora3d.spec` → arquivo único, sem console,
  em `dist\Calculadora3D.exe`.
- **Linux:** `bash packaging/linux/build_appimage.sh 0.2.0` →
  `dist/Calculadora3D-0.2.0-x86_64.AppImage` (usa `calculadora3d-linux.spec`;
  precisa de `xvfb` para o teste de abertura no final).

O ícone é gerado por `python tools/make_icon.py` (grava
`calculadora3d/resources/icon.png` e `icon.ico`).

## Lançar uma versão

1. Suba a versão em `calculadora3d/__init__.py` (`__version__ = "0.3.0"`) e
   faça o commit.
2. Crie e envie a tag com o mesmo número:

   ```
   git tag v0.3.0
   git push origin main v0.3.0
   ```

O workflow `Release` (`.github/workflows/release.yml`) roda os testes, gera o
`.exe` e o AppImage, abre cada um por alguns segundos para conferir e publica a
release com os dois arquivos. Se a tag não bater com `__version__` ou qualquer
etapa falhar, nada é publicado. Para testar o processo sem publicar, use
**Actions → Release → Run workflow**: os arquivos ficam como artefatos do run.

## Fora do escopo da v1

Taxas de marketplace, frete e impostos; projetos do PrusaSlicer e Cura;
estimativa de peso por volume para arquivos não fatiados; preços de filamento
online; múltiplos usuários e sincronização.
