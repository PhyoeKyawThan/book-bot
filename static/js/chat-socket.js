const chat_socket = {
    socket: null,
    open() {
        if (!this.socket.connected) {
            this.socket.connect();
        }
        this.socket.once("connect", () => {
            this.socket.emit("chat_open");
        });
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

        this.socket.on("chat_init", (data)=>{
            callback(data);
        })
    },

    sendMessage(text) {
        if (!this.socket.connected) return;

        this.socket.send({
            message: text
        });
    }
};