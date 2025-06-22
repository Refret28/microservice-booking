let currentBookingId = null;

function viewPaymentDetails(bookingId) {
    fetch(`/booking_details/${bookingId}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => {
        if (response.ok) {
            window.location.href = `/booking_details/${bookingId}`;
        } else {
            return response.json().then(errorData => {
                if (errorData.detail === "Данные о бронировании не найдены") {
                    const notification = document.getElementById('deletingNotification');
                    notification.style.display = 'block';
                    setTimeout(() => {
                        notification.style.display = 'none';
                    }, 1000);
                } else {
                    console.error('Ошибка:', errorData);
                    alert('Ошибка при загрузке данных о бронировании');
                }
            });
        }
    })
    .catch(error => {
        console.error('Ошибка при отправке запроса:', error);
        alert('Ошибка при загрузке данных о бронировании');
    });
}

function openCancelModal(bookingId) {
    currentBookingId = bookingId;
    document.getElementById('cancelModal').style.display = 'flex';
}

function closeCancelModal() {
    document.getElementById('cancelModal').style.display = 'none';
    currentBookingId = null;
}

function closeErrorModal() {
    document.getElementById('errorModal').style.display = 'none';
}

document.addEventListener("DOMContentLoaded", function () {
    document.getElementById('cancelModal').style.display = 'none';
    document.getElementById('errorModal').style.display = 'none';
    document.getElementById('successNotification').style.display = 'none';
    document.getElementById('deletingNotification').style.display = 'none';

    const confirmButton = document.getElementById('confirmCancel');
    if (confirmButton) {
        confirmButton.addEventListener('click', async () => {
            if (currentBookingId) {
                try {
                    const response = await fetch(`/cancel_booking/${currentBookingId}`, {
                        method: 'DELETE',
                        headers: { 'Content-Type': 'application/json' }
                    });

                    closeCancelModal();
                    if (response.ok) {
                        console.log(`Бронирование ${currentBookingId} успешно отменено`);
                        const notification = document.getElementById('successNotification');
                        notification.style.display = 'block';
                        setTimeout(() => {
                            notification.style.display = 'none';
                            const bookingElement = document.querySelector(`.booking-item[data-booking-id="${currentBookingId}"]`);
                            if (bookingElement) {
                                bookingElement.remove();
                            }
                            window.location.reload();
                        }, 1000);
                    } else {
                        const errorData = await response.json();
                        console.error('Ошибка отмены бронирования:', errorData);
                        document.getElementById('errorModal').style.display = 'flex';
                    }
                } catch (error) {
                    console.error('Ошибка при отправке запроса на отмену:', error);
                    closeCancelModal();
                    document.getElementById('errorModal').style.display = 'flex';
                }
            }
        });
    }
});