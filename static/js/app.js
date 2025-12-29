const chatIcon = document.querySelector("#chat-bot #icon");
const chatArea = document.getElementById("chat-area");
const closeBtn = document.getElementById("close-chat-area");

closeBtn.addEventListener("click", () => {
    chatIcon.style.display = "block";
    chatArea.style.display = "none";
})

chatIcon.addEventListener("click", (e) => {
    e.stopPropagation();
    chatIcon.style.display = "none";
    chatArea.style.display = "flex";
});

document.addEventListener("click", () => {
    chatIcon.style.display = "block";
    chatArea.style.display = "none";
});

chatArea.addEventListener("click", (e) => {
    e.stopPropagation(); 
});
