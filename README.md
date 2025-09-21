# Projeto de Chat Peer-to-Peer (P2P)

Implementação de um sistema de chat distribuído com arquitetura P2P para a disciplina de Sistemas Distribuídos, Concorrência e Paralelismo.

## Descrição

Este projeto é uma aplicação de chat em linha de comando que opera de forma descentralizada. Diferente de um modelo cliente-servidor tradicional, não há um servidor central; cada participante da rede (chamado de "peer" ou "nó") atua simultaneamente como cliente e servidor.

A aplicação demonstra conceitos fundamentais de sistemas distribuídos, como comunicação via sockets, gerenciamento de estado distribuído (lista de pares) e concorrência através de multithreading.

## Funcionalidades Principais

* **Arquitetura P2P Real:** Cada instância do programa é um nó autônomo na rede.
* **Concorrência com Threads:** Uso intensivo da biblioteca `threading` do Python para:
    * Escutar por novas conexões de peers.
    * Gerenciar múltiplas conexões ativas simultaneamente.
    * Permitir que o usuário envie e receba mensagens ao mesmo tempo.
* **Comunicação via Sockets TCP:** A base da comunicação entre os nós é feita utilizando sockets TCP para garantir a entrega das mensagens.
* **Protocolo de Mensagem Simples:** As mensagens são formatadas com um identificador de remetente (`remetente|conteúdo`) para que os usuários saibam quem enviou cada mensagem.
* **Mecanismo de Broadcast (Flooding):** Uma mensagem enviada por um nó é retransmitida para todos os seus vizinhos, garantindo que a mensagem se espalhe por toda a rede.

## Pré-requisitos

* Python 3.6 ou superior.
* Nenhuma biblioteca externa é necessária (apenas bibliotecas padrão do Python são utilizadas).

## Como Executar

A aplicação é executada a partir do terminal. A topologia da rede é formada dinamicamente, conectando um novo nó a um nó que já está online.

A sintaxe do comando é:
```sh
python peer_final.py <SEU_HOST> <SUA_PORTA> [HOST_DO_PEER_EXISTENTE] [PORTA_DO_PEER_EXISTENTE]
```
* `<SEU_HOST>`: O endereço de host que este peer usará (ex: `localhost`).
* `<SUA_PORTA>`: A porta em que este peer escutará por conexões (ex: `9001`).
* `[HOST_DO_PEER_EXISTENTE]` (Opcional): O host de um peer já na rede ao qual você deseja se conectar.
* `[PORTA_DO_PEER_EXISTENTE]` (Opcional): A porta do peer já na rede.

### Exemplo de Uso com 3 Peers

Para testar a rede, abra três terminais diferentes:

**1. Terminal 1 - Iniciar o primeiro Peer (Nó de Bootstrap):**
Este peer apenas escutará por conexões.
```sh
python peer_final.py localhost 9000
```

**2. Terminal 2 - Iniciar o segundo Peer:**
Este peer escutará na porta `9001` e se conectará ao primeiro peer na porta `9000`.
```sh
python peer_final.py localhost 9001 localhost 9000
```

**3. Terminal 3 - Iniciar o terceiro Peer:**
Este peer escutará na porta `9002` e se conectará ao segundo peer na porta `9001`, formando uma cadeia.
```sh
python peer_final.py localhost 9002 localhost 9001
```

Agora, a rede está formada. Qualquer mensagem digitada em um dos terminais será retransmitida para todos os outros, com a identificação de quem a enviou.


ᓚᘏᗢ