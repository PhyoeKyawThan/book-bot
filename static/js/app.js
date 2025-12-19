const chatIcon = document.querySelector("#chat-bot #icon");
const chatArea = document.getElementById("chat-area");

chatIcon.addEventListener("click", () => {
    chatIcon.style.display = "none";
    chatArea.style.display = "flex";
})