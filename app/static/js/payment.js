const formContainer = document.getElementById('form-container');
const formTitle = document.getElementById('form-title');
const form = document.getElementById('form');
const amount = window.amount || 0;
const user_id = parseInt(window.user_id || getUserIdFromUrl());

console.log("payment.js: amount при инициализации:", amount);
console.log("payment.js: user_id при инициализации:", user_id);

form.addEventListener('click', async (event) => {
    if (event.target.id === 'submit-data') {
        const carNumberInput = document.getElementById('car_number');
        const carBrand = document.getElementById('car_brand');
        const carNumber = carNumberInput.value.trim();
        const carBrandValue = carBrand.value.trim();

        const isValidCarNumber = /^[0-9а-яА-Я]{6,10}$/.test(carNumber);

        if (!isValidCarNumber) {
            carNumberInput.setCustomValidity('Номер автомобиля должен быть длиной 6-10 символов (буквы и цифры).');
            carNumberInput.reportValidity();
            return;
        } else {
            carNumberInput.setCustomValidity('');
        }

        if (!carBrandValue) {
            carBrand.setCustomValidity('Пожалуйста, выберите марку автомобиля.');
            carBrand.reportValidity();
            return;
        } else {
            carBrand.setCustomValidity('');
        }

        if (isNaN(user_id)) {
            console.error("Неверный user_id:", user_id);
            showNotification("Ошибка: Неверный идентификатор пользователя");
            return;
        }

        const carData = {
            car_number: carNumber,
            car_brand: carBrandValue,
            user_id: user_id  
        };

        try {
            event.target.disabled = true;
            console.log("Отправляем авто для user_id:", user_id);
            
            const carResponse = await fetch('/cars', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(carData),
            });

            if (!carResponse.ok) {
                const errorData = await carResponse.json();
                console.error("Ошибка при сохранении автомобиля:", errorData.detail || errorData);
                showNotification(`Ошибка: ${errorData.detail || "Не удалось сохранить автомобиль"}`);
                return;
            }

            console.log("Данные об автомобиле успешно сохранены");

            const paymentResponse = await fetch('/pay', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: user_id }),
            });

            if (paymentResponse.redirected) {
                window.location.href = paymentResponse.url;
                return;
            }

            if (paymentResponse.ok) {
                const responseData = await paymentResponse.json();
                console.log("Успех:", responseData);
                if (responseData.telegram_url) {
                    window.open(responseData.telegram_url, '_blank');
                    setTimeout(() => {
                        window.location.href = `/waiting/${user_id}`;
                    }, 500);
                } else {
                    console.error("Ссылка на Telegram-бот не получена");
                    showNotification("Ошибка: не удалось получить ссылку для оплаты");
                }
            } else {
                const errorData = await paymentResponse.json();
                console.error("Ошибка сервера:", errorData.detail || errorData);
                showNotification(`Ошибка: ${errorData.detail || "Ошибка при оплате"}`);
            }
        } catch (error) {
            console.error('Ошибка при отправке данных:', error);
            showNotification('Ошибка при отправке данных');
        } finally {
            event.target.disabled = false;
        }
    }
});

function getUserIdFromUrl() {
    const pathParts = window.location.pathname.split('/');
    return pathParts[pathParts.length - 1];
}

function showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => {
        notification.remove();
    }, 3000);
}


function setupCancelButton() {
    const cancelBtn = document.getElementById('cancel-booking');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            showModal('cancelBookingModal');
        });
    }
}

function showModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.remove('hide');
    modal.classList.add('show');
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.remove('show');
    modal.classList.add('hide');
}

document.addEventListener('DOMContentLoaded', () => {
    setupCancelButton();

    document.querySelector('#cancelBookingModal .close').addEventListener('click', () => {
        closeModal('cancelBookingModal');
    });

    document.querySelector('#cancelBookingModal .cancel').addEventListener('click', () => {
        closeModal('cancelBookingModal');
    });

    document.getElementById('confirmCancelBtn').addEventListener('click', async () => {
        try {
            const response = await fetch(`/cancel_booking/${user_id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            if (response.ok) {
                window.location.href = `/main_page?user_id=${user_id}`;
            } else {
                const errorData = await response.json();
                showNotification(`Ошибка при отмене: ${errorData.detail}`);
            }
        } catch (error) {
            showNotification('Ошибка при отмене бронирования');
        }
    });

    window.addEventListener('click', (event) => {
        if (event.target === document.getElementById('cancelBookingModal')) {
            closeModal('cancelBookingModal');
        }
    });
});