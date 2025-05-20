# configuracao.py
import json
import urllib.request
import os
import logging

# Usaremos o logger configurado no script principal
logger = logging.getLogger(__name__)

# URL padrão para a configuração, caso não seja fornecida.
# É altamente recomendável que você compile com a URL correta ou use o argumento /configurl.
URL_CONFIG_PADRAO = "http://localhost/config_protetor.json" # Altere para a URL real da sua rede

def carregar_configuracao(url_config_remota=None):
    """
    Carrega a configuração de uma URL remota ou de um caminho UNC.
    Se url_config_remota for um caminho UNC, tenta ler diretamente.
    """
    if url_config_remota is None:
        url_config_remota = URL_CONFIG_PADRAO
        logger.info(f"Nenhuma URL de configuração fornecida, usando padrão: {URL_CONFIG_PADRAO}")

    logger.info(f"Tentando carregar configuração de: {url_config_remota}")
    config = None

    try:
        if url_config_remota.startswith('\\\\'): # Caminho UNC
            logger.info(f"Detectado caminho UNC: {url_config_remota}")
            if os.path.exists(url_config_remota) and os.path.isfile(url_config_remota):
                with open(url_config_remota, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info("Configuração carregada com sucesso de caminho UNC.")
            else:
                logger.error(f"Arquivo de configuração não encontrado ou não é um arquivo: {url_config_remota}")
                raise FileNotFoundError(f"Arquivo de configuração não encontrado: {url_config_remota}")
        elif url_config_remota.startswith('http://') or url_config_remota.startswith('https://'): # URL HTTP/S
            logger.info(f"Detectada URL HTTP/S: {url_config_remota}")
            # Adicionar header para tentar evitar cache de proxy/navegador
            req = urllib.request.Request(url_config_remota, headers={'Cache-Control': 'no-cache', 'Pragma': 'no-cache'})
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = response.read().decode('utf-8')
                    config = json.loads(data)
                    logger.info("Configuração carregada com sucesso de URL HTTP/S.")
                else:
                    logger.error(f"Falha ao carregar configuração. Status: {response.status}")
                    raise ConnectionError(f"Falha ao carregar configuração. Status: {response.status}")
        else:
            logger.error(f"Formato de URL/caminho de configuração inválido: {url_config_remota}")
            raise ValueError("Formato de URL/caminho de configuração inválido.")

    except urllib.error.URLError as e:
        logger.error(f"Erro de URL ao carregar configuração: {e}")
        raise ConnectionError(f"Não foi possível conectar à URL de configuração: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON da configuração: {e}")
        raise ValueError(f"Formato JSON inválido: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado ao carregar configuração: {e}")
        raise

    if config:
        # Validações básicas
        required_keys = ["pasta_imagens_rede", "tempo_exibicao_imagem_segundos", "pasta_cache_local_subpath"]
        for key in required_keys:
            if key not in config:
                msg_erro = f"Chave obrigatória '{key}' não encontrada na configuração."
                logger.error(msg_erro)
                raise KeyError(msg_erro)
        
        # Construir o caminho completo da pasta de cache
        appdata_local_path = os.getenv('LOCALAPPDATA')
        if not appdata_local_path:
            # Fallback se LOCALAPPDATA não estiver definido (muito raro em Windows modernos)
            appdata_local_path = os.path.join(os.getenv('USERPROFILE', '.'), 'AppData', 'Local')
            logger.warning(f"Variável de ambiente LOCALAPPDATA não encontrada. Usando fallback: {appdata_local_path}")
        
        config["pasta_cache_local_completa"] = os.path.join(appdata_local_path, config["pasta_cache_local_subpath"])
        logger.info(f"Caminho completo do cache local definido para: {config['pasta_cache_local_completa']}")
        
        logger.info(f"Configuração carregada e processada: {json.dumps(config, indent=2)}")
    return config

if __name__ == '__main__':
    # Configurar um logger básico para o teste do configuracao.py
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logger_test = logging.getLogger() # Pega o root logger configurado acima

    try:
        # Simular um config_remota.json localmente para teste
        test_config_file = "temp_config_test.json"
        test_config_content = {
            "versao_config": "1.1.0",
            "pasta_imagens_rede": "\\\\TEST_SERVER\\SHARE\\images", # Use um caminho UNC válido se quiser testar o acesso
            "pasta_cache_local_subpath": "ProtetorTelaUniversidadeTeste/CacheImagens",
            "tempo_exibicao_imagem_segundos": 5,
            "extensoes_permitidas": [".jpg", ".png"],
            "url_configuracao_remota": f"file:///{os.path.abspath(test_config_file).replace(os.sep, '/')}"
        }
        with open(test_config_file, "w", encoding='utf-8') as f:
            json.dump(test_config_content, f, indent=2)

        logger_test.info(f"Testando carregamento de: {test_config_file}")
        # Para testar com arquivo local (simulando UNC ou HTTP local)
        # Se for um caminho de arquivo local, ele deve ser absoluto para o teste aqui
        # O código principal espera UNC (\\) ou HTTP(S)
        # Para simular UNC, use um caminho de arquivo existente no formato UNC ou um arquivo local
        # config = carregar_configuracao(os.path.abspath(test_config_file)) # Isso não testará a lógica UNC/HTTP diretamente
        
        # Testando com um servidor HTTP local (ex: python -m http.server 8001 na pasta do temp_config_test.json)
        # config = carregar_configuracao("http://localhost:8001/temp_config_test.json")

        # Testando com um caminho UNC simulado (crie o arquivo nesse caminho)
        # Exemplo: config = carregar_configuracao(r"\\localhost\c$\temp\temp_config_test.json")
        # Certifique-se que o arquivo existe no caminho acima
        
        # Para o teste simples, vamos apenas usar o arquivo local via file:// (não suportado pelo código, mas para ilustrar)
        # Ou, melhor, vamos criar um arquivo e usar seu caminho absoluto como se fosse UNC (o que não é ideal, mas funciona se o código não validar estritamente \\)
        # A forma mais robusta de testar é com um servidor HTTP ou um compartilhamento de rede real.

        # Teste básico que deve funcionar se o arquivo existir
        config_teste = carregar_configuracao(os.path.abspath(test_config_file))


        if config_teste:
            logger_test.info("Configuração de teste carregada com sucesso:")
            logger_test.info(json.dumps(config_teste, indent=4))
        else:
            logger_test.error("Falha ao carregar configuração de teste.")
            
    except Exception as e:
        logger_test.error(f"Erro no teste de carregamento de configuração: {e}", exc_info=True)
    finally:
        if os.path.exists(test_config_file):
            os.remove(test_config_file)