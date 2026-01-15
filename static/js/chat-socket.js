const chat_socket = {
    socket: null,
    open() {
        if (!this.socket.connected) {
            this.socket.connect();
        }
    },

    close() {
        if (this.socket.connected) {
            this.socket.disconnect();
        }
    },

    onConnect(callback) {
        this.socket.on("connect", () => {
            statusActive();
            callback?.();
        });
    },

    onDisconnect(callback) {
        this.socket.on("disconnect", () => {
            statusDisconnected();
            callback?.();
        });
    },

    onMessage(callback) {
        this.socket.on("message", (data) => {
            callback(data);
        });
    },

    sendMessage(text) {
        if (!this.socket.connected) return;

        this.socket.send({
            message: text
        });
    }
};