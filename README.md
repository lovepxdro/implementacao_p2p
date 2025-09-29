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
  - O input do usuário roda em um processo separado, permitindo paralelismo real em múltiplos núcleos de CPU.  
- **Sincronização:**  
  - Uso de `threading.Lock` para garantir acesso seguro ao dicionário de peers.  
- **Comunicação entre Processos/Threads:**  
  - Uso de `multiprocessing.Queue` para enviar mensagens do processo de input para as threads que fazem broadcast.  
- **Mensagens Identificadas:**  
  - Cada mensagem inclui nome e host:porta do remetente.  
- **Broadcast (Flooding):**  
  - Toda mensagem é retransmitida para todos os peers conectados.  

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

ᓚᘏᗢ