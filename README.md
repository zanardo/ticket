# ticket

`ticket` é um sistema simples de chamados para pequenos departamentos de TI,
para o acompanhamento de casos em aberto sobre qualquer coisa (bugs de software,
tarefas, demandas de helpdesk, etc).

Ele é desenvolvido em Python, e possui poucas dependências de bibliotecas
externas. ticket embute seu próprio servidor web e utiliza um banco de dados
SQLite para armazenar os dados, simplificando sua instalação e manutenção.

## Dependências

`ticket` precisa do Python 3.7.

## Instalando ticket

Criando o virtualenv do Python e instalando as dependências:

```bash
make
```

## Iniciando ticket

Iniciar o servidor web:

```bash
make run
```

Como padrão, o servidor web escuta no host `127.0.0.1`, e na porta `5000`. O
banco de dados default é no arquivo `ticket.db`, o qual será criado
automaticamente na primeira inicialização. As configurações poderão ser
alteradas editando-se o arquivo `config.py` e reiniciando o aplicativo.

Agora basta acessar o sistema via navegador. O usuário padrão é `admin` com
senha `admin`. Ao acessar o sistema, crie um usuário para você, dê poderes de
administrador, e exclua o usuário padrão `admin`.
