CONFIG = {
    # Endereço onde o servidor irá ouvir as conexões
    "host": "127.0.0.1",
    "port": 5000,

    # Habilitar debug - não usar em produção!
    "debug": False,

    # Arquivo do banco de dados SQLite. Será criado automaticamente
    # caso não exista.
    "dbname": "data/ticket.db",

    # Título das páginas.
    "title": "ticket",

    # Descrição das prioridades. É possível adicionar mais prioridades
    # caso seja necessário.
    "priodesc": {
        1: 'Urgente',
        2: 'Atenção',
        3: 'Normal',
        4: 'Baixa',
        5: 'Baixíssima',
    },

    # Cores das prioridades.
    "priocolor": {
        1: '#FF8D8F',
        2: '#99CC00',
        3: '#FF9966',
        4: '#6DF2B2',
        5: '#9FEFF2',
    },

    # Tamanho máximo (em bytes) de arquivos anexados aos tickets
    "filemaxsize": 128000,

    # Servidor de e-mail para envio
    "mailsmtp": '127.0.0.1',

    # Funcionalidades ativas. Comentar a linha para desativar a funcionalidade.
    "features": [
        'timetrack',    # Tempo trabalhado
        'adminonly',    # Restrição de tickets para administradores
        'fileattach',   # Arquivos anexos
        'dependency',   # Dependências entre tickets
        'datedue',      # Data de previsão de solução
        'mail',         # Envio de comentários por e-mail
    ],
}


def config(key):
    return CONFIG.get(key)
