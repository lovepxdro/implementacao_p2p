# Projeto de Chat Peer-to-Peer (P2P)

Implementação de um sistema de chat distribuído com arquitetura P2P para a disciplina de **Fundamentos da Computação Concorrente, Paralela e Distribuída**.

## Descrição

Este projeto é uma aplicação de chat em linha de comando que opera de forma descentralizada.  
Diferente de um modelo cliente-servidor tradicional, não há servidor central: cada participante da rede (chamado de *peer* ou *nó*) atua simultaneamente como cliente e servidor.

A aplicação demonstra conceitos fundamentais de sistemas distribuídos, como comunicação via sockets, gerenciamento de estado distribuído (lista de pares) concorrência através de multithreading, paralelismo, sincronização e comunicação entre processos via fila(Queue).

## Funcionalidades Principais

- **Arquitetura P2P:** Cada instância do programa é um nó autônomo.  
- **Concorrência com Threads:**  
  - Escuta por novas conexões.  
  - Gerencia múltiplos peers conectados simultaneamente.  
  - Consome mensagens da fila interna para envio.  
- **Paralelismo com Processos:**  
  - Processo dedicado (`log_worker`) grava o histórico de eventos em disco em paralelo à execução principal.  
- **Sincronização:**  
  - Uso de `threading.Lock` para garantir acesso seguro ao dicionário de peers.  
- **Mensagens Identificadas:**  
  - Cada mensagem inclui nome e host:porta do remetente.  
- **Broadcast (Flooding):**  
  - Toda mensagem é retransmitida para todos os peers conectados.  
- **Interface CLI Amigável:**  
  - Prompt interativo (`nome> `).  
  - Comandos para listar peers, conectar, encerrar e exibir ajuda.  

## Pré-requisitos

- Python **3.6+**  
- Nenhuma biblioteca externa (apenas bibliotecas padrão do Python).  

## Como Executar

A aplicação é executada pelo terminal.  
Agora o usuário também precisa escolher um **nome** para se identificar no chat.  

```sh
python peer.py <SEU_HOST> <SUA_PORTA> <SEU_NOME> [HOST_DO_PEER_EXISTENTE] [PORTA_DO_PEER_EXISTENTE]
```

- `<SEU_HOST>`: IP ou `localhost`  
- `<SUA_PORTA>`: porta local em que o peer vai escutar  
- `<SEU_NOME>`: nome que será exibido no chat  
- `[HOST_DO_PEER_EXISTENTE]` e `[PORTA_DO_PEER_EXISTENTE]` (opcionais): peer já online ao qual se conectar  

---

### Exemplo com 3 Peers

**1. Primeiro Peer (Bootstrap):**
```sh
python peer.py 127.0.0.1 5000 Julia
```

**2. Segundo Peer (conectando ao primeiro):**
```sh
python peer.py 127.0.0.1 5001 Pedro 127.0.0.1 5000
```

**3. Terceiro Peer (conectando ao segundo):**
```sh
python peer.py 127.0.0.1 5002 Ana 127.0.0.1 5001
```

Saída esperada ao trocar mensagens (Terminal de Julia):  
```
Você: ola      
[Pedro (127.0.0.1:5001) disse]: ola                                               
[Ana (127.0.0.1:5002) disse]: oi
```

## Histórico de Mensagens

Cada peer cria/atualiza automaticamente um arquivo `chat_history_<porta>.log` na
mesma pasta do projeto. O arquivo registra:

- Início e fim da sessão.
- Conexões e desconexões de peers.
- Mensagens enviadas e recebidas.

Isso demonstra a comunicação entre threads (fila de mensagens) e processos
(fila de log) e facilita a auditoria das interações.

## Comandos da Interface CLI

Enquanto a aplicação está rodando, você pode utilizar comandos especiais:

| Comando | Descrição |
|---------|-----------|
| `/help` | Mostra a lista de comandos disponíveis. |
| `/connect HOST PORT` | Conecta dinamicamente a outro peer ativo. |
| `/peers` | Exibe os peers atualmente conectados a você. |
| `/quit` | Encerra o peer local de forma graciosa. |

Qualquer texto que não comece com `/` é enviado imediatamente como mensagem para a
rede. A dica aparece no prompt assim que o peer sobe: *“Interface pronta. Digite
/help para ver os comandos disponíveis.”*

ᓚᘏᗢ
