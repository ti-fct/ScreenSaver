
# 🖼️ Protetor de Tela Universitário com Cache (Python)

Protetor de tela para Windows 10/11 desenvolvido em **Python**. Ele exibe imagens de uma **pasta de rede configurada via JSON remoto**, com suporte a **cache local offline**. Ideal para ambientes universitários ou corporativos.

---

## ✅ Funcionalidades

- 📷 **Exibição de Imagens:** Suporte a `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`.
- 💾 **Cache Local:** Imagens da rede são armazenadas em cache local (`%LOCALAPPDATA%`) para exibição offline.
- 🌐 **Configuração Remota:** Configurações via JSON remoto (HTTP/S ou UNC).
- 🖤 **Fallback de Segurança:** Tela preta caso nenhuma imagem esteja disponível.
- ⚙️ **Suporte aos Argumentos Padrão do Windows:**
  - `/s`: Inicia o protetor de tela.
  - `/p <HWND>`: Preview (usado pelo Windows).
  - `/c`: Abre a janela de configuração (informativa).
- 📝 **Log Detalhado:** Arquivo de log em `%TEMP%\protetor_tela_uni_cache.log`.

---

## 📁 Estrutura do Projeto

```plaintext
protetor_tela.py           # Script principal (UI e execução)
configuracao.py            # Carregamento e validação da configuração remota
config_remota.json         # Exemplo de configuração remota (JSON)
```

---

## 🛠️ Requisitos

- Python 3.x
- Pillow:  
```bash
pip install Pillow
```

---

## 🔧 Exemplo de Configuração Remota (`config_remota.json`)

```json
{
    "versao_config": "1.1.0",
    "pasta_imagens_rede": "\\SEU_SERVIDOR\\COMPARTILHAMENTO\\imagens_universidade",
    "pasta_cache_local_subpath": "ProtetorTelaUniversidade/CacheImagens",
    "tempo_exibicao_imagem_segundos": 10,
    "extensoes_permitidas": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
    "url_configuracao_remota": "URL_PARA_ESTE_PROPRIO_ARQUIVO_CONFIG_JSON_RAW"
}
```

### Campos:

| Campo                         | Descrição |
|------------------------------|-----------|
| `versao_config`              | Versão da estrutura de configuração. |
| `pasta_imagens_rede`         | Caminho UNC com as imagens. |
| `pasta_cache_local_subpath`  | Subpasta no `%LOCALAPPDATA%` onde o cache será salvo. |
| `tempo_exibicao_imagem_segundos` | Tempo de exibição por imagem. |
| `extensoes_permitidas`       | Extensões válidas para exibição. |
| `url_configuracao_remota`    | Caminho para o próprio arquivo JSON (permite autoatualização). |

---

## ⚙️ Ajuste Inicial

1. Configure e hospede seu `config_remota.json`.
2. No `configuracao.py`, altere a constante:

```python
URL_CONFIG_PADRAO = "https://raw.githubusercontent.com/seu_usuario/seu_repo/main/config_remota.json"
```

3. (Opcional) Use linha de comando para sobrescrever a URL:

```bash
python protetor_tela.py /s /configurl:SUA_URL_DO_CONFIG_REMOTA_JSON
```

---

## ▶️ Executando

### Rodar protetor de tela:

```bash
python protetor_tela.py /s
```

### Modo configuração (informativo):

```bash
python protetor_tela.py /c
```

### Preview (usado pelo Windows):

```bash
python protetor_tela.py /p <HWND>
```

---

## 🏗️ Compilação para `.scr` (Protetor de Tela Windows)

Requer [PyInstaller](https://pyinstaller.org/):

```bash
pip install pyinstaller
```

### Gerar executável:

```bash
pyinstaller --name ProtetorTelaUniCache --onefile --windowed --add-data "configuracao.py:." protetor_tela.py
```

- `--onefile`: Gera um único arquivo `.exe`.
- `--windowed`: Sem console.
- `--add-data`: Inclui `configuracao.py` no bundle.

### Finalização:

1. O arquivo será gerado em `dist/ProtetorTelaUniCache.exe`.
2. Renomeie para `.scr`:

```bash
ren ProtetorTelaUniCache.exe ProtetorTelaUniCache.scr
```

---

## 🖥️ Instalação como Protetor de Tela

1. Copie o `.scr` para `C:\Windows\System32\` (requer administrador).
2. Ou clique com botão direito no `.scr` e selecione **"Instalar"**.
3. Vá em **Configurações > Protetor de Tela** e selecione o `ProtetorTelaUniCache`.

---

## 🧪 Diagnóstico

Verifique o log gerado:

```bash
%TEMP%\protetor_tela_uni_cache.log
```

Contém mensagens de erro, falhas de acesso à rede ou problemas de cache.

---

## 📄 Licença

Este projeto está licenciado sob a .
