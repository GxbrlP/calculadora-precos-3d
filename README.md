# Calculadora 3D

Aplicativo de desktop (Python + PySide6) que lê projetos fatiados do Bambu Studio
e calcula o custo e o preço de venda de uma impressão 3D: filamento, energia,
taxa de falha, mão de obra, embalagem e margens (varejo, atacado e revenda).
Os valores ficam em um banco SQLite local; nada é enviado para a internet.

## Arquivo de entrada

O app espera o `.gcode.3mf` exportado do Bambu Studio com **Ctrl+G** (Exportar
G-code fatiado). Cada arquivo contém uma placa; arraste vários arquivos para
somar as placas de um mesmo produto.

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

## Gerar o .exe (Windows)

O build do executável roda no Windows, com o ambiente acima instalado
(`pip install -e ".[dev]"` já inclui o PyInstaller):

```
pyinstaller calculadora3d.spec
```

O resultado é um arquivo único, sem console, em `dist\Calculadora3D.exe`.
O ícone é gerado por `python tools/make_icon.py` (grava
`calculadora3d/resources/icon.png` e `icon.ico`).

## Fora do escopo da v1

Taxas de marketplace, frete e impostos; projetos do PrusaSlicer e Cura;
estimativa de peso por volume para arquivos não fatiados; preços de filamento
online; múltiplos usuários e sincronização.
