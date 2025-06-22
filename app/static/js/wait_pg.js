const path = window.location.pathname;
const userId = path.split('/').pop(); 
console.log("UserId:", userId)

let countdown = 3;

function updateCountdown() {
    document.getElementById('countdown-timer').innerText = countdown;
    countdown--;

    if (countdown < 0) {
        window.location.href = `/main_page?user_id=${userId}`;
    }
}

setInterval(updateCountdown, 1000);