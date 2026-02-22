const chat_socket = {
    socket: null,
    
    init: function() {
        this.socket = io("/bot", {
            autoConnect: false,
            reconnection: true,
            reconnectionAttempts: 5,
            reconnectionDelay: 1000
        });
    },
    
    open: function() {
        if (this.socket) {
            this.socket.connect();
        }
    },
    
    close: function() {
        if (this.socket && this.socket.connected) {
            this.socket.disconnect();
        }
    },
    
    onConnect: function(callback) {
        if (this.socket) {
            this.socket.on('connect', callback);
        }
    },
    
    onDisconnect: function(callback) {
        if (this.socket) {
            this.socket.on('disconnect', callback);
        }
    },
    
    onMessage: function(callback) {
        if (this.socket) {
            this.socket.on('message', callback);
        }
    },
    
    sendMessage: function(message) {
        if (this.socket && this.socket.connected) {
            this.socket.emit('message', { message: message });
        } else {
            console.warn('Socket not connected. Message not sent.');
            addBotMessage("Connection lost. Please reopen the chat.");
        }
    },
    
    reconnect: function() {
        if (this.socket && !this.socket.connected) {
            this.socket.connect();
        }
    }
};

chat_socket.init();