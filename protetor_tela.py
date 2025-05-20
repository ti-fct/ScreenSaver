# protetor_tela.py
import tkinter as tk
from PIL import Image, ImageTk # pip install Pillow
import os
import sys
import random
import time
import logging
import ctypes # Para obter dimensões da tela e interagir com o preview do Windows
import shutil # Para cópia de arquivos (cache)

# Importar nosso módulo de configuração
import configuracao

# Configuração básica de logging
# É importante que o nome do arquivo de log seja único ou gerenciado para não crescer indefinidamente
# ou ter problemas de concorrência se várias instâncias rodarem (ex: preview e config ao mesmo tempo).
# Usar um nome de arquivo com PID pode ser uma opção para depuração, mas um fixo é mais comum.
log_file_path = os.path.join(os.getenv('TEMP', '.'), 'protetor_tela_uni_cache.log')
logging.basicConfig(
    level=logging.INFO, # Mude para DEBUG para mais detalhes durante o desenvolvimento
    format='%(asctime)s - %(levelname)s - %(name)s - %(module)s - %(funcName)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, mode='a', encoding='utf-8'), # 'a' para append
        logging.StreamHandler(sys.stdout) # Para ver logs no console durante o desenvolvimento
    ]
)
logger = logging.getLogger("ProtetorTelaPrincipal") # Usar um nome específico para o logger principal

# --- Constantes e Configurações Globais ---
CONFIG = None
IMAGENS_DISPONIVEIS = [] # Lista de caminhos completos para as imagens a serem exibidas
INDICE_IMAGEM_ATUAL = 0
JANELA_PRINCIPAL = None
LABEL_IMAGEM = None
HANDLE_JANELA_PREVIEW = None
PROGRAM_NAME = "ProtetorTelaUniversidadeCache"
MODO_APENAS_TELA_PRETA = False # Flag para indicar que apenas tela preta deve ser mostrada

# --- Funções de Cache e Carregamento de Imagens ---
def sincronizar_cache_e_carregar_imagens():
    """
    Tenta sincronizar imagens da rede para o cache local.
    Carrega a lista de imagens da rede (se disponível) ou do cache.
    Define MODO_APENAS_TELA_PRETA se nenhuma imagem for encontrada.
    Retorna True se imagens foram carregadas, False caso contrário.
    """
    global IMAGENS_DISPONIVEIS, MODO_APENAS_TELA_PRETA, CONFIG
    IMAGENS_DISPONIVEIS = []
    MODO_APENAS_TELA_PRETA = False # Reseta o estado

    if not CONFIG:
        logger.error("Configuração não disponível. Impossível sincronizar cache ou carregar imagens.")
        MODO_APENAS_TELA_PRETA = True
        return False

    pasta_rede = CONFIG["pasta_imagens_rede"]
    pasta_cache = CONFIG["pasta_cache_local_completa"]
    extensoes = CONFIG.get("extensoes_permitidas", [".jpg", ".jpeg", ".png", ".gif", ".bmp"])

    # 1. Garantir que a pasta de cache exista
    try:
        os.makedirs(pasta_cache, exist_ok=True)
        logger.info(f"Pasta de cache '{pasta_cache}' verificada/criada.")
    except OSError as e:
        logger.error(f"Não foi possível criar a pasta de cache '{pasta_cache}': {e}. Cache não será usado efetivamente.")
        # Se não puder criar o cache, o comportamento dependerá da disponibilidade da rede.

    # 2. Tentar acessar a rede e sincronizar com o cache
    rede_acessivel = False
    arquivos_rede_dict = {} # {nome_arquivo: caminho_completo}

    logger.info(f"Tentando acessar pasta de rede: '{pasta_rede}'")
    if os.path.isdir(pasta_rede):
        rede_acessivel = True
        logger.info(f"Pasta de rede '{pasta_rede}' acessível.")
        try:
            # Listar arquivos da rede
            for nome_arquivo in os.listdir(pasta_rede):
                if any(nome_arquivo.lower().endswith(ext) for ext in extensoes):
                    caminho_origem = os.path.join(pasta_rede, nome_arquivo)
                    if os.path.isfile(caminho_origem):
                        arquivos_rede_dict[nome_arquivo] = caminho_origem
            
            logger.info(f"Encontrados {len(arquivos_rede_dict)} arquivos de imagem na rede.")

            # Sincronizar: copiar da rede para o cache se necessário
            arquivos_cache_existentes = {f for f in os.listdir(pasta_cache) if os.path.isfile(os.path.join(pasta_cache, f))}
            
            for nome_arquivo, caminho_origem in arquivos_rede_dict.items():
                caminho_destino_cache = os.path.join(pasta_cache, nome_arquivo)
                copiar = False
                if nome_arquivo not in arquivos_cache_existentes:
                    copiar = True
                    logger.debug(f"Arquivo '{nome_arquivo}' não está no cache. Copiando.")
                else:
                    # Compara data de modificação para decidir se atualiza o cache
                    try:
                        if os.path.getmtime(caminho_origem) > os.path.getmtime(caminho_destino_cache):
                            copiar = True
                            logger.debug(f"Arquivo '{nome_arquivo}' na rede é mais novo. Atualizando cache.")
                    except FileNotFoundError: # Arquivo no cache pode ter sido removido externamente
                        copiar = True
                        logger.debug(f"Arquivo '{nome_arquivo}' não encontrado no cache (FileNotFound). Copiando.")
                    except OSError as e_mtime:
                        logger.warning(f"Não foi possível verificar data de modificação para '{nome_arquivo}': {e_mtime}. Copiando por segurança.")
                        copiar = True 
                
                if copiar:
                    try:
                        shutil.copy2(caminho_origem, caminho_destino_cache) # copy2 preserva metadados
                        logger.info(f"Copiado/Atualizado '{nome_arquivo}' da rede para o cache.")
                    except Exception as e_copy:
                        logger.error(f"Erro ao copiar '{nome_arquivo}' da rede para o cache: {e_copy}")
            
            # Limpar cache: remover arquivos do cache que não existem mais na rede
            arquivos_para_remover_do_cache = arquivos_cache_existentes - set(arquivos_rede_dict.keys())
            for nome_arquivo_obsoleto in arquivos_para_remover_do_cache:
                try:
                    os.remove(os.path.join(pasta_cache, nome_arquivo_obsoleto))
                    logger.info(f"Removido '{nome_arquivo_obsoleto}' do cache (não existe mais na rede).")
                except Exception as e_remove:
                    logger.error(f"Erro ao remover '{nome_arquivo_obsoleto}' do cache: {e_remove}")

        except Exception as e:
            logger.error(f"Erro durante a listagem ou sincronização de arquivos da rede: {e}")
            rede_acessivel = False # Considera rede inacessível se houver erro na sincronização
    else:
        logger.warning(f"Pasta de rede '{pasta_rede}' não está acessível ou não é um diretório.")

    # 3. Carregar lista de imagens a serem exibidas
    if rede_acessivel:
        logger.info("Usando imagens diretamente da pasta de rede.")
        IMAGENS_DISPONIVEIS = list(arquivos_rede_dict.values())
    elif os.path.isdir(pasta_cache): # Se rede não acessível, tentar usar o cache
        logger.info(f"Rede indisponível. Tentando usar imagens da pasta de cache '{pasta_cache}'.")
        try:
            for nome_arquivo in os.listdir(pasta_cache):
                if any(nome_arquivo.lower().endswith(ext) for ext in extensoes):
                    caminho_completo = os.path.join(pasta_cache, nome_arquivo)
                    if os.path.isfile(caminho_completo):
                        IMAGENS_DISPONIVEIS.append(caminho_completo)
            if IMAGENS_DISPONIVEIS:
                 logger.info(f"Carregadas {len(IMAGENS_DISPONIVEIS)} imagens do cache.")
            else:
                logger.warning(f"Nenhuma imagem encontrada no cache: '{pasta_cache}'.")
        except Exception as e:
            logger.error(f"Erro ao listar imagens do cache '{pasta_cache}': {e}")
            IMAGENS_DISPONIVEIS = [] # Garante que está vazia se houver erro
    
    if IMAGENS_DISPONIVEIS:
        random.shuffle(IMAGENS_DISPONIVEIS)
        logger.info(f"Total de {len(IMAGENS_DISPONIVEIS)} imagens prontas para exibição.")
        return True
    else:
        logger.warning("Nenhuma imagem disponível (nem da rede, nem do cache). Protetor exibirá tela preta.")
        MODO_APENAS_TELA_PRETA = True
        return False

# --- Funções Auxiliares ---
def fechar_protetor(event=None):
    """Fecha a janela do protetor de tela."""
    global JANELA_PRINCIPAL
    if JANELA_PRINCIPAL:
        logger.info("Fechando protetor de tela.")
        JANELA_PRINCIPAL.quit()
        JANELA_PRINCIPAL.destroy()
        JANELA_PRINCIPAL = None
        sys.exit(0) # Encerra o script Python

def mostrar_proxima_imagem():
    """Exibe a próxima imagem ou mantém a tela preta."""
    global INDICE_IMAGEM_ATUAL, LABEL_IMAGEM, JANELA_PRINCIPAL, CONFIG, MODO_APENAS_TELA_PRETA

    if not JANELA_PRINCIPAL or not CONFIG:
        logger.warning("Tentativa de mostrar imagem sem janela principal ou configuração carregada.")
        if JANELA_PRINCIPAL: # Se a janela existe mas algo deu errado, agenda fechamento
            JANELA_PRINCIPAL.after(1000, fechar_protetor)
        return
    
    if MODO_APENAS_TELA_PRETA or not IMAGENS_DISPONIVEIS:
        logger.debug("Modo tela preta ou sem imagens. Nenhuma imagem será exibida.")
        if LABEL_IMAGEM: # Garante que a label esteja configurada para preto (sem imagem)
            LABEL_IMAGEM.configure(image=None, bg='black')
            LABEL_IMAGEM.image = None # Limpar referência
        # Não precisa agendar próxima chamada se for apenas tela preta.
        # A janela permanecerá preta. Se for /s, eventos do usuário fecharão.
        return

    # Se chegamos aqui, há imagens para mostrar
    caminho_imagem = IMAGENS_DISPONIVEIS[INDICE_IMAGEM_ATUAL]
    INDICE_IMAGEM_ATUAL = (INDICE_IMAGEM_ATUAL + 1) % len(IMAGENS_DISPONIVEIS)

    try:
        logger.debug(f"Carregando imagem: {caminho_imagem}")
        img_pil = Image.open(caminho_imagem)

        largura_tela = JANELA_PRINCIPAL.winfo_width()
        altura_tela = JANELA_PRINCIPAL.winfo_height()

        if largura_tela <= 1 or altura_tela <= 1: # Janela ainda não renderizada
            logger.debug("Dimensões da janela ainda não disponíveis, tentando novamente em 100ms.")
            JANELA_PRINCIPAL.after(100, mostrar_proxima_imagem)
            return

        # Redimensionar imagem para caber na tela, mantendo a proporção
        img_pil.thumbnail((largura_tela, altura_tela), Image.Resampling.LANCZOS)
        img_tk = ImageTk.PhotoImage(img_pil)

        if LABEL_IMAGEM is None: # Deveria ter sido criado em iniciar_protetor_tela
            logger.error("LABEL_IMAGEM não foi inicializado. Criando agora.")
            LABEL_IMAGEM = tk.Label(JANELA_PRINCIPAL, background='black')
            LABEL_IMAGEM.pack(expand=True, fill=tk.BOTH)
        
        LABEL_IMAGEM.configure(image=img_tk, bg='black') # Garante bg preto caso a imagem tenha alfa
        LABEL_IMAGEM.image = img_tk # Manter referência para evitar garbage collection

        logger.debug(f"Imagem '{os.path.basename(caminho_imagem)}' exibida.")

    except FileNotFoundError:
        logger.error(f"Arquivo de imagem não encontrado (sumiu?): {caminho_imagem}")
        IMAGENS_DISPONIVEIS.pop(IMAGENS_DISPONIVEIS.index(caminho_imagem)) # Remove da lista
        if not IMAGENS_DISPONIVEIS:
            logger.warning("Nenhuma imagem válida restante após FileNotFoundError.")
            MODO_APENAS_TELA_PRETA = True
            mostrar_proxima_imagem() # Chamada para limpar a imagem atual e ficar preto
            return
        JANELA_PRINCIPAL.after(100, mostrar_proxima_imagem) # Tenta a próxima imagem
        return
    except Exception as e:
        logger.error(f"Erro ao carregar ou exibir imagem '{caminho_imagem}': {e}", exc_info=True)
        # Opcional: remover imagem problemática da lista
        # IMAGENS_DISPONIVEIS.pop(IMAGENS_DISPONIVEIS.index(caminho_imagem))
        # if not IMAGENS_DISPONIVEIS: MODO_APENAS_TELA_PRETA = True
        JANELA_PRINCIPAL.after(100, mostrar_proxima_imagem) # Tenta a próxima imagem
        return

    # Agendar a próxima troca de imagem
    tempo_exibicao_ms = int(CONFIG.get("tempo_exibicao_imagem_segundos", 10) * 1000)
    JANELA_PRINCIPAL.after(tempo_exibicao_ms, mostrar_proxima_imagem)


def iniciar_protetor_tela(modo_preview=False, handle_janela_pai_preview=None, url_config_remota=None):
    """Inicia a janela principal do protetor de tela."""
    global JANELA_PRINCIPAL, CONFIG, HANDLE_JANELA_PREVIEW, MODO_APENAS_TELA_PRETA, LABEL_IMAGEM

    logger.info(f"Iniciando protetor de tela. Modo preview: {modo_preview}, Handle pai: {handle_janela_pai_preview}")
    
    if url_config_remota:
        logger.info(f"URL de configuração fornecida: {url_config_remota}")
    else:
        logger.info(f"URL de configuração não fornecida, usando padrão de configuracao.py: {configuracao.URL_CONFIG_PADRAO}")


    try:
        CONFIG = configuracao.carregar_configuracao(url_config_remota)
    except Exception as e:
        logger.critical(f"Falha CRÍTICA ao carregar configuração: {e}. Protetor de tela usará tela preta.", exc_info=True)
        MODO_APENAS_TELA_PRETA = True
        # Não retorna, continua para criar a janela preta.
    
    if CONFIG: # Se a config carregou, tentar sincronizar e carregar imagens
        sincronizar_cache_e_carregar_imagens() # Define MODO_APENAS_TELA_PRETA se falhar
    else: # Se config falhou no try-except, MODO_APENAS_TELA_PRETA já é True
        logger.info("Configuração não pôde ser carregada. MODO_APENAS_TELA_PRETA ativado.")

    JANELA_PRINCIPAL = tk.Tk()
    JANELA_PRINCIPAL.title(PROGRAM_NAME)
    JANELA_PRINCIPAL.configure(background='black') # Fundo preto padrão
    if not modo_preview: # Cursor some apenas em tela cheia
        JANELA_PRINCIPAL.configure(cursor='none')

    if modo_preview and handle_janela_pai_preview:
        HANDLE_JANELA_PREVIEW = handle_janela_pai_preview
        logger.info(f"Configurando para modo preview com handle: {HANDLE_JANELA_PREVIEW}")
        try:
            JANELA_PRINCIPAL.update_idletasks() # Garante que a janela Tkinter existe e tem um HWND
            hwnd_tkinter = JANELA_PRINCIPAL.winfo_id()
            
            rect = ctypes.wintypes.RECT()
            if not ctypes.windll.user32.GetClientRect(HANDLE_JANELA_PREVIEW, ctypes.byref(rect)):
                logger.error(f"Falha ao obter dimensões da janela de preview (GetClientRect). Erro: {ctypes.get_last_error()}")
                fechar_protetor()
                return

            largura_preview = rect.right - rect.left
            altura_preview = rect.bottom - rect.top
            
            logger.info(f"Dimensões da janela de preview: {largura_preview}x{altura_preview}")
            if largura_preview <=0 or altura_preview <=0:
                logger.error("Dimensões da janela de preview inválidas. Abortando modo preview.")
                fechar_protetor()
                return

            ctypes.windll.user32.SetParent(hwnd_tkinter, HANDLE_JANELA_PREVIEW)
            # Estilo para janela filha sem bordas
            style = ctypes.windll.user32.GetWindowLongW(hwnd_tkinter, ctypes.wintypes.DWORD(-16)) # GWL_STYLE
            style = style & ~0x00C00000 # WS_CAPTION
            style = style & ~0x00040000 # WS_THICKFRAME (borda de redimensionamento)
            style = style & ~0x00800000 # WS_BORDER (borda fina)
            style = style | 0x40000000   # WS_CHILD
            ctypes.windll.user32.SetWindowLongW(hwnd_tkinter, ctypes.wintypes.DWORD(-16), style)
            
            # Move e redimensiona a janela Tkinter para preencher a janela de preview
            ctypes.windll.user32.MoveWindow(hwnd_tkinter, 0, 0, largura_preview, altura_preview, True)
            # JANELA_PRINCIPAL.geometry(f"{largura_preview}x{altura_preview}+0+0") # MoveWindow deve ser suficiente
            JANELA_PRINCIPAL.resizable(False, False)
        except Exception as e_preview:
            logger.error(f"Erro ao configurar modo preview: {e_preview}", exc_info=True)
            fechar_protetor() # Fecha se o preview falhar
            return
    else:
        # Modo tela cheia (/s)
        JANELA_PRINCIPAL.attributes('-fullscreen', True)
        JANELA_PRINCIPAL.bind("<KeyPress>", fechar_protetor)
        JANELA_PRINCIPAL.bind("<Motion>", fechar_protetor) # Qualquer movimento do mouse
        JANELA_PRINCIPAL.bind("<ButtonPress>", fechar_protetor) # Qualquer clique

    # Cria o Label que exibirá as imagens ou ficará preto
    LABEL_IMAGEM = tk.Label(JANELA_PRINCIPAL, background='black')
    LABEL_IMAGEM.pack(expand=True, fill=tk.BOTH)

    if MODO_APENAS_TELA_PRETA or not IMAGENS_DISPONIVEIS:
        logger.info("Protetor iniciado em modo tela preta (sem imagens para exibir).")
        # Nenhuma ação adicional necessária, a label já está preta e vazia.
    else:
        logger.info("Protetor iniciado com imagens. Exibindo a primeira.")
        mostrar_proxima_imagem()

    JANELA_PRINCIPAL.mainloop()
    logger.info("Loop principal do Tkinter encerrado. Protetor de tela finalizado.")


def mostrar_configuracao_dialogo(url_config_remota_param=None):
    """Exibe uma janela simples de 'configuração' (mais informativa)."""
    # Não usar a CONFIG global aqui, pois esta função pode ser chamada
    # independentemente do protetor estar rodando em modo /s ou /p.
    # Carrega a configuração apenas para exibir as informações.
    logger.info("Modo configuração (/c) solicitado.")
    
    temp_config_data = None
    config_url_usada = url_config_remota_param or configuracao.URL_CONFIG_PADRAO
    
    try:
        temp_config_data = configuracao.carregar_configuracao(config_url_usada)
    except Exception as e:
        logger.error(f"Erro ao carregar configuração para tela de info: {e}", exc_info=True)
        msg_erro = (
            f"Erro ao carregar configuração de:\n'{config_url_usada}'\n\n"
            f"Detalhes: {str(e)}\n\n"
            f"Verifique o arquivo de log para mais informações:\n{log_file_path}"
        )
        ctypes.windll.user32.MessageBoxW(0, msg_erro, f"{PROGRAM_NAME} - Erro de Configuração", 0x10) # MB_ICONERROR
        return

    if not temp_config_data:
        msg_erro = (
            f"Não foi possível carregar a configuração de:\n'{config_url_usada}'.\n\n"
            f"Verifique se a URL está correta e acessível, e se o arquivo JSON é válido.\n\n"
            f"Log: {log_file_path}"
        )
        ctypes.windll.user32.MessageBoxW(0, msg_erro, f"{PROGRAM_NAME} - Erro de Configuração", 0x10)
        return

    info_msg = (
        f"{PROGRAM_NAME}\n(Com Cache, Sem Atualização Automática)\n\n"
        f"Versão da Configuração: {temp_config_data.get('versao_config', 'Desconhecida')}\n"
        f"URL de Configuração: {config_url_usada}\n"
        f"Pasta de Imagens Remota: {temp_config_data.get('pasta_imagens_rede', 'Não configurada')}\n"
        f"Pasta de Cache Local: {temp_config_data.get('pasta_cache_local_completa', 'Não configurada')}\n"
        f"Tempo por Imagem: {temp_config_data.get('tempo_exibicao_imagem_segundos', 'N/A')} segundos\n\n"
        f"Este protetor de tela busca imagens de uma pasta de rede e as armazena em cache local.\n"
        f"Se a rede estiver indisponível, imagens do cache serão usadas.\n"
        f"Se não houver imagens ou a configuração falhar, uma tela preta será exibida.\n\n"
        f"Arquivo de log: {log_file_path}"
    )
    ctypes.windll.user32.MessageBoxW(0, info_msg, f"{PROGRAM_NAME} - Informações", 0x40) # MB_ICONINFORMATION


def main():
    logger.info(f"'{PROGRAM_NAME}' iniciado com argumentos: {sys.argv}")
    
    # Argumento customizado para URL de configuração: /configurl:<URL_OU_CAMINHO_UNC>
    url_config_arg_cmd = None
    args_para_processar = list(sys.argv[1:]) # Copia para poder modificar

    # Extrai /configurl se presente
    temp_args = []
    for arg in args_para_processar:
        if arg.lower().startswith("/configurl:"):
            try:
                url_config_arg_cmd = arg.split(":", 1)[1]
                logger.info(f"URL de configuração fornecida por argumento de linha de comando: {url_config_arg_cmd}")
            except IndexError:
                logger.warning(f"Argumento /configurl malformado: {arg}")
        else:
            temp_args.append(arg)
    args_para_processar = temp_args


    # O primeiro argumento restante (após remover /configurl) define o modo
    modo_arg_principal = args_para_processar[0].lower() if args_para_processar else "/s" # Padrão para /s

    if modo_arg_principal == "/s":
        logger.info("Modo: Rodar protetor de tela (/s)")
        iniciar_protetor_tela(url_config_remota=url_config_arg_cmd)
    elif modo_arg_principal == "/p":
        if len(args_para_processar) > 1:
            try:
                handle_str = args_para_processar[1]
                handle_preview_arg = int(handle_str) # O segundo argumento é o handle da janela
                logger.info(f"Modo: Preview (/p) na janela com handle: {handle_preview_arg}")
                iniciar_protetor_tela(modo_preview=True, handle_janela_pai_preview=handle_preview_arg, url_config_remota=url_config_arg_cmd)
            except ValueError:
                logger.error(f"Handle da janela de preview inválido: {handle_str}", exc_info=True)
                sys.exit(1)
            except IndexError:
                logger.error("Handle da janela de preview não fornecido para o modo /p.", exc_info=True)
                sys.exit(1)
        else:
            logger.error("Argumento de handle da janela de preview ausente para o modo /p.")
            sys.exit(1)
    elif modo_arg_principal.startswith("/c"): # Trata /c e /c:HWND (HWND é ignorado por nós)
        logger.info(f"Modo: Configuração ({modo_arg_principal})")
        mostrar_configuracao_dialogo(url_config_remota_param=url_config_arg_cmd)
    else:
        # Argumento desconhecido ou ausente (além de /configurl)
        # O Windows pode chamar sem argumentos se o usuário clicar em "Propriedades" ou "Configurações"
        # diretamente no arquivo .scr. Alguns sistemas chamam /c, outros nada.
        logger.warning(f"Argumento principal desconhecido ou padrão: '{modo_arg_principal}'. Exibindo diálogo de informações.")
        mostrar_configuracao_dialogo(url_config_remota_param=url_config_arg_cmd)

if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        # SystemExit é esperado quando o protetor de tela fecha normalmente.
        logger.info(f"'{PROGRAM_NAME}' encerrado via SystemExit.")
    except Exception as e_fatal:
        # Captura qualquer outra exceção não tratada no nível mais alto.
        logger.critical(f"Erro fatal não tratado no script principal: {e_fatal}", exc_info=True)
        # Tenta mostrar uma mensagem de erro para o usuário, se possível.
        try:
            error_message_display = (
                f"Ocorreu um erro crítico e inesperado no protetor de tela '{PROGRAM_NAME}'.\n\n"
                f"Erro: {str(e_fatal)}\n\n"
                f"Consulte o arquivo de log para detalhes técnicos:\n{log_file_path}"
            )
            ctypes.windll.user32.MessageBoxW(0, error_message_display, f"{PROGRAM_NAME} - Erro Crítico", 0x10) # MB_ICONERROR
        except Exception as e_msgbox:
            # Se nem o MessageBox funcionar, não há muito mais a fazer.
            logger.error(f"Falha ao exibir MessageBox de erro crítico: {e_msgbox}", exc_info=True)
        sys.exit(1) # Termina com código de erro