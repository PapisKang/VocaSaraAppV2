class Chatbox {
  constructor() {
    // Initialisation des éléments HTML nécessaires à la chatbox
    this.args = {
      openButton: document.querySelector('.chatbox__button'),
      chatBox: document.querySelector('.chatbox__support'),
      sendButton: document.querySelector('.send__button'),
      clearButton: document.querySelector('.clear_button')
    };

    // Initialisation de l'état de la chatbox et du tableau de messages
    this.state = false;
    this.messages = [];

    // Récupération de l'historique de chat de l'utilisateur depuis le stockage local
    const storedMessages = localStorage.getItem('chat_history');
    if (storedMessages) {
      this.messages = JSON.parse(storedMessages);
    }

    // Ajout d'un listener pour le bouton "Effacer"
    this.args.clearButton.addEventListener('click', () => this.clearChatHistory());
  }

  display() {
    $(this.args.chatBox).draggable(); // Rendre le chatbox déplaçable
    
    // Récupération des éléments HTML
    const { openButton, chatBox, sendButton } = this.args;

    // Ajout des listeners pour ouvrir/fermer la chatbox et envoyer un message
    openButton.addEventListener('click', () => this.toggleState(chatBox));

    sendButton.addEventListener('click', () => this.onSendButton(chatBox));

    // Ajout d'un listener pour la touche Entrée
    const node = chatBox.querySelector('input');
    node.addEventListener('keyup', ({ key }) => {
      if (key === 'Enter') {
        this.onSendButton(chatBox);
      }
    });

    // Affichage de l'historique de chat de l'utilisateur
    this.updateChatText(chatBox);
  }

  // Fonction pour ouvrir ou fermer la chatbox
  toggleState(chatbox) {
    this.state = !this.state;

    // Ajoute ou supprime la classe chatbox--active
    if (this.state) {
        chatbox.classList.add('chatbox--active');
    } else {
        chatbox.classList.remove('chatbox--active');
    }
}


  // Fonction pour envoyer un message
  onSendButton(chatbox) {
    // Récupération de la valeur de l'input
    const textField = chatbox.querySelector('input');
    const text1 = textField.value;

    // Vérification que l'input n'est pas vide
    if (text1 === '') {
      return;
    }

    // Ajout du message de l'utilisateur au tableau de messages
    const msg1 = { name: 'User', message: text1 };
    this.messages.push(msg1);

    // Ajout d'un message de chatbot qui réfléchit
    this.addThinkingMessage();

    // Appel de l'API pour obtenir une réponse à partir du message de l'utilisateur
    fetch($SCRIPT_ROOT + '/predict', {
      method: 'POST',
      body: JSON.stringify({ message: text1 }),
      mode: 'cors',
      headers: {
        'Content-Type': 'application/json'
      }
    })
      .then((r) => r.json())
      .then((r) => {
        // Retrait du message de chatbot qui réfléchit et ajout de la réponse de l'API avec un effet de typing
        this.removeThinkingMessage();
        this.addTypingMessage(r.answer);

        // Effacement de l'input
        textField.value = '';

        // Mise à jour de l'historique de chat de l'utilisateur dans le stockage local
        localStorage.setItem('chat_history', JSON.stringify(this.messages));
      })
      .catch((error) => {
        console.error('Error:', error);

        // Retrait du message de chatbot qui réfléchit
        this.removeThinkingMessage();

        // Mise à jour de la chatbox
        this.updateChatText(chatbox);

        // Effacement de l'input
        textField.value = '';
      });
  }

  // Fonction pour ajouter un message de chatbot qui réfléchit
  addThinkingMessage() {
    const msg = { name: 'Vocasara', message: '...' };
    this.messages.push(msg);
    this.updateChatText(this.args.chatBox);

    // Mise à jour de l'historique de chat de l'utilisateur dans le stockage local
    localStorage.setItem('chat_history', JSON.stringify(this.messages));
  }

  // Fonction pour retirer le dernier message de chatbot qui réfléchit
  removeThinkingMessage() {
    const lastMessage = this.messages[this.messages.length - 1];
    if (lastMessage && lastMessage.name === 'Vocasara' && lastMessage.message === '...') {
      this.messages.pop();
    }
  }

  // Fonction pour ajouter un message de chatbot avec un effet de typing
  addTypingMessage(answer) {
    // Ajout du message de chatbot avec un effet de typing
    const msg = { name: 'Vocasara', message: '' };
    this.messages.push(msg);

    // Mise à jour de la chatbox avec le message vide
    this.updateChatText(this.args.chatBox);

    // Ajout du texte avec un effet de typing
    const typingSpeed = 10; // Vitesse de typing en millisecondes
    let currentMessage = '';
    let currentIndex = 0;
    const chatmessage = this.args.chatBox.querySelector('.chatbox__messages');
    const typingInterval = setInterval(() => {
      if (currentIndex < answer.length) {
        currentMessage += answer[currentIndex];
        this.messages[this.messages.length - 1].message = currentMessage;
        this.updateChatText(this.args.chatBox);
        currentIndex++;
      } else {
        // Retrait du message qui réfléchit une fois que l'effet de typing est terminé
        clearInterval(typingInterval);
        this.removeThinkingMessage();

        // Mise à jour de l'historique de chat de l'utilisateur dans le stockage local
        localStorage.setItem('chat_history', JSON.stringify(this.messages));
      }
    }, typingSpeed);
  }

  // Fonction pour effacer l'historique de chat de l'utilisateur
  clearChatHistory() {
    // Effacement de l'historique de chat de l'utilisateur
    this.messages = [];

    // Mise à jour de la chatbox
    this.updateChatText(this.args.chatBox);

    // Effacement de l'historique de chat de l'utilisateur dans le stockage local
    localStorage.removeItem('chat_history');
  }

  // Fonction pour mettre à jour la chatbox
  updateChatText(chatbox) {
    // Récupération de la position de la barre de défilement avant la mise à jour
    const scrollTop = chatbox.querySelector('.chatbox__messages').scrollTop;

    // Création du HTML pour afficher les messages
    let html = '';
    this.messages.slice().reverse().forEach(function (item, index) {
      if (item.name === 'Vocasara') {
        html += '<div class="messages__item messages__item--operator">' + item.message + '</div>';
      } else {
        html += '<div class="messages__item messages__item--visitor">' + item.message + '</div>';
      }
    });

    const chatmessage = chatbox.querySelector('.chatbox__messages');
    chatmessage.innerHTML = html;

    // Restauration de la position de la barre de défilement après la mise à jour
    chatmessage.scrollTop = scrollTop;
  }
}

const chatbox = new Chatbox();
chatbox.display();