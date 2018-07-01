# Este script inicia o servidor de desenvolvimento, com o modo debug ativado.
# **NÃO USAR EM PRODUÇÃO!**

import sys
import os

if __name__ == '__main__':
    sys.path.append(os.getcwd())

    from ticket.app import app

    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True,
        reloader=True,
    )
