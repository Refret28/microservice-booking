let openModals = 0;
let scrollPosition = 0;
let currentFloorIndex = 0;
let availableFloors = [];
let allSpots = [];
let parkingPrices = [];
let selectedSpot = null;

function showSpotErrorNotification() {
    console.log('Вызов showSpotErrorNotification');
    const notification = document.getElementById('spotErrorNotification');
    if (!notification) {
        console.error('Уведомление spotErrorNotification не найдено');
        return;
    }
    console.log('Показываем уведомление: Пожалуйста, выберите парковочное место');
    notification.classList.remove('hide');
    notification.classList.add('show');
    setTimeout(() => {
        notification.classList.remove('show');
        notification.classList.add('hide');
        console.log('Уведомление скрыто');
    }, 1000);
}

function preventScroll(e) {
    const target = e.target.closest('#spotsList');
    if (target && window.getComputedStyle(target).overflowY === 'auto') {
        const canScrollUp = target.scrollTop > 0;
        const canScrollDown = target.scrollTop < target.scrollHeight - target.clientHeight;
        const deltaY = e.deltaY || e.wheelDelta || 0;
        if ((deltaY < 0 && canScrollUp) || (deltaY > 0 && canScrollDown)) {
            return;
        }
    }
    e.preventDefault();
    e.stopPropagation();
}

function disableScroll() {
    scrollPosition = window.scrollY;
    document.body.style.position = 'fixed';
    document.body.style.top = `-${scrollPosition}px`;
    document.body.style.width = '100%';
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.paddingRight = `${scrollbarWidth}px`;
    document.body.classList.add('no-scroll');
    document.documentElement.classList.add('no-scroll');
    document.body.addEventListener('touchmove', preventScroll, { passive: false });
    document.body.addEventListener('wheel', preventScroll, { passive: false });
}

function enableScroll() {
    document.body.removeEventListener('touchmove', preventScroll);
    document.body.removeEventListener('wheel', preventScroll);
    document.body.style.position = '';
    document.body.style.top = '';
    document.body.style.width = '';
    document.body.style.paddingRight = '';
    document.body.classList.remove('no-scroll');
    document.documentElement.classList.remove('no-scroll');
    window.scrollTo(0, scrollPosition);
}

function showModal(modalId) {
    console.log(`Открытие ${modalId}, openModals: ${openModals + 1}`);
    const modal = document.getElementById(modalId);
    if (!modal) {
        console.error(`Модальное окно с ID ${modalId} не найдено`);
        return;
    }
    modal.classList.remove('hide');
    modal.classList.add('show');
    openModals++;
    if (openModals === 1) {
        disableScroll();
    }
}

function closeModal(modalId) {
    console.log(`Закрытие ${modalId}, openModals: ${openModals - 1}`);
    const modal = document.getElementById(modalId);
    if (modal && modal.classList.contains('show')) {
        modal.classList.remove('show');
        modal.classList.add('hide');
        openModals = Math.max(0, openModals - 1);
        if (openModals === 0) {
            enableScroll();
        }
    }
}

const parkingSchemes = {
    'ул. Володарского, 11': {
        'default': '/static/images/parking_schemes/volodarskogo.png'
    },
    'ул. Кураева, 10': {
        '1': '/static/images/parking_schemes/kuraeva_floor1.png',
        '2': '/static/images/parking_schemes/kuraeva_floor2.png',
        '3': '/static/images/parking_schemes/kuraeva_floor3.png',
        '4': '/static/images/parking_schemes/kuraeva_floor4.png',
        '5': '/static/images/parking_schemes/kuraeva_floor5.png',
    },
    'ул. Максима Горького, 52': {
        'default': '/static/images/parking_schemes/maksima_gorkogo.png'
    },
};

async function loadParkingPrices() {
    try {
        const response = await fetch('/parking_prices');
        if (!response.ok) throw new Error(`Ошибка загрузки цен: ${response.status}`);
        parkingPrices = await response.json();
    } catch (error) {
        console.error('Ошибка при загрузке цен:', error);
        alert('Не удалось загрузить цены парковок.');
    }
}

var closeBtn = document.getElementById("modalCloseBtn");
if (closeBtn) {
    closeBtn.onclick = function() {
        closeModal("parkingModal");
    };
}

window.onclick = function(event) {
    if (event.target == document.getElementById("parkingModal")) {
        closeModal("parkingModal");
    }
};

function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    if (sidebar) sidebar.classList.toggle("open");
}

function closeSidebar() {
    const sidebar = document.getElementById("sidebar");
    if (sidebar) sidebar.classList.remove("open");
}

const locationSelect = document.getElementById('location');
const priceInput = document.getElementById('price');
if (locationSelect && priceInput) {
    locationSelect.addEventListener('change', function() {
        selectedSpot = null;
        priceInput.value = 'Выберите место';
        document.getElementById('selected_spot').value = '';
        const floorElement = document.getElementById('floor');
        if (floorElement) {
            floorElement.value = '';
        }
    });
}

document.addEventListener("DOMContentLoaded", async () => {
    await loadParkingPrices();

    function initializeMap(defaultLocation) {
        const [coords, address] = defaultLocation.split('|');
        const [lat, lng] = coords.split(',').map(Number);
        const map = L.map('map').setView([lat, lng], 14);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 18,
            attribution: '© <a href="https://www.openstreetmap.org/">OpenStreetMap</a>'
        }).addTo(map);
        const marker = L.marker([lat, lng]).addTo(map);
        L.circle([53.1907,  45.013], {
            color: 'blue',
            fillColor: '#649cf5',
            fillOpacity: 0.5,
            radius: 450
        }).addTo(map);
        document.getElementById("address").textContent = address;
        return { map, marker };
    }

    function updateMap(mapData, locationSelect) {
        const selectedValue = locationSelect.value;
        if (!selectedValue) return;
        const [coords, address] = selectedValue.split('|');
        const [lat, lng] = coords.split(',').map(Number);
        mapData.marker.setLatLng([lat, lng]);
        mapData.map.setView([lat, lng], 14);
        document.getElementById("address").textContent = address;
    }

    function handleFormSubmission() {
        const bookButton = document.getElementById("bookButton");
        if (!bookButton) {
            console.error("Кнопка бронирования не найдена");
            return;
        }
    
        bookButton.addEventListener("click", async (event) => {
            event.preventDefault();
    
            const locationElement = document.getElementById("location");
            const startDatetimeElement = document.getElementById("start_datetime");
            const endDatetimeElement = document.getElementById("end_datetime");
            const userIdElement = document.getElementById('user_id');
            const selectedSpotInput = document.getElementById('selected_spot');
    
            console.log('Проверка формы:');
            console.log('location:', locationElement?.value);
            console.log('start_datetime:', startDatetimeElement?.value);
            console.log('end_datetime:', endDatetimeElement?.value);
            console.log('selected_spot:', selectedSpotInput?.value);
    
            let isValid = true;
            let allOtherFieldsFilled = true;
    
            if (!locationElement || !locationElement.value) {
                if (locationElement) locationElement.setCustomValidity('Пожалуйста, выберите локацию.');
                isValid = false;
                allOtherFieldsFilled = false;
            } else {
                locationElement.setCustomValidity('');
            }
    
            if (!startDatetimeElement || !startDatetimeElement.value) {
                if (startDatetimeElement) startDatetimeElement.setCustomValidity('Пожалуйста, выберите дату и время начала.');
                isValid = false;
                allOtherFieldsFilled = false;
            } else {
                startDatetimeElement.setCustomValidity('');
            }
    
            if (!endDatetimeElement || !endDatetimeElement.value) {
                if (endDatetimeElement) endDatetimeElement.setCustomValidity('Пожалуйста, выберите дату и время окончания.');
                isValid = false;
                allOtherFieldsFilled = false;
            } else {
                endDatetimeElement.setCustomValidity('');
            }
    
            if (!selectedSpotInput || !selectedSpotInput.value) {
                if (allOtherFieldsFilled) {
                    console.log('Все поля кроме selected_spot заполнены, показываем уведомление');
                    showSpotErrorNotification();
                } else {
                    console.log('Не все поля заполнены, используем setCustomValidity для selected_spot');
                    if (selectedSpotInput) selectedSpotInput.setCustomValidity('Пожалуйста, выберите парковочное место.');
                }
                isValid = false;
            } else {
                if (selectedSpotInput) selectedSpotInput.setCustomValidity('');
            }
    
            if (!isValid) {
                console.log('Форма невалидна');
                document.getElementById('booking-form').reportValidity();
                return;
            }
    
            const [coordinates, address] = locationElement.value.split("|");
            const startDatetime = new Date(startDatetimeElement.value);
            const endDatetime = new Date(endDatetimeElement.value);
            const currentDatetime = new Date();
    
            if (startDatetime < currentDatetime || endDatetime < currentDatetime) {
                console.error("Ошибка: Даты не могут быть прошлыми.");
                showModal('pastDateModal');
                return;
            }
    
            const timeDifference = (endDatetime - startDatetime) / (1000 * 60);
            if (timeDifference < 30) {
                console.error("Ошибка: Разница между началом и концом должна составлять как минимум 30 минут.");
                showModal('timeDifferenceModal');
                return;
            }
    
            let spots;
            try {
                const response = await fetch(`/api/parking_spots?location=${encodeURIComponent(locationElement.value)}&user_id=${userIdElement.value}`);
                if (!response.ok) {
                    throw new Error(`Ошибка сервера: ${response.status} ${response.statusText}`);
                }
                spots = await response.json();
                console.log('Полученные места для проверки:', spots);
    
                const hasFloors = spots.some(spot => spot.floor !== null && spot.floor !== undefined);
                const spotNumber = parseInt(selectedSpotInput.value);
                let spot;
    
                if (hasFloors && selectedSpot?.floor) {
                    spot = spots.find(s => s.spot_number == spotNumber && s.floor == selectedSpot.floor && s.is_available);
                } else {
                    spot = spots.find(s => s.spot_number == spotNumber && s.floor === null && s.is_available);
                }
    
                if (!spot) {
                    const floorStr = hasFloors && selectedSpot?.floor ? `на этаже ${selectedSpot.floor}` : 'без этажа';
                    console.error(`Место ${spotNumber} ${floorStr} недоступно в полученных данных:`, spots);
                    alert(`Место ${spotNumber} ${floorStr} стало недоступно. Пожалуйста, выберите другое место.`);
                    return;
                }
            } catch (error) {
                console.error('Ошибка при проверке доступности:', error);
                alert(`Не удалось проверить доступность места: ${error.message}`);
                return;
            }
    
            const bookingData = {
                user_id: parseInt(userIdElement.value),
                address: address.trim(),
                spot_number: parseInt(selectedSpotInput.value),
                start_time: startDatetimeElement.value,
                end_time: endDatetimeElement.value
            };
    
            if (selectedSpot?.floor && spots.some(spot => spot.floor !== null && spot.floor !== undefined)) {
                bookingData.floor = parseInt(selectedSpot.floor);
            }
    
            console.log('Отправляемые данные:', bookingData);
    
            try {
                const response = await fetch('/book', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(bookingData)
                });
    
                if (response.ok) {
                    const data = await response.json();
                    if (data && data.booking_id) {
                        console.log("Бронирование успешно:", data);
                        showBookingInfoModal(data.spot_number);
                    } else {
                        console.error("Сервер вернул пустой или некорректный ответ:", data);
                        alert("Бронирование не удалось. Попробуйте снова.");
                    }
                } else if (response.status === 409) {
                    showModal('occupiedParkingModal');
                } else {
                    const errorData = await response.json();
                    console.error("Ошибка сервера:", errorData);
                    alert(`Ошибка бронирования: ${errorData.detail || 'Неизвестная ошибка'}`);
                }
            } catch (error) {
                console.error("Ошибка при отправке данных:", error);
                alert(`Ошибка при отправке данных: ${error.message}`);
            }
        });
    }

    function showBookingInfoModal(spotId) {
        const bookingInfoMessage = document.getElementById("bookingInfoMessage");
        if (bookingInfoMessage) {
            bookingInfoMessage.innerHTML = `Ваше парковочное место: <b>${spotId}</b><br><br>Всю информацию о бронировании можете посмотреть на странице профиля после оплаты.`;
            showModal('bookingInfoModal');
        }
    }

    const modalCloseBookingInfoBtn = document.getElementById("modalCloseBookingInfoBtn");
    if (modalCloseBookingInfoBtn) {
        modalCloseBookingInfoBtn.onclick = function() {
            closeModal('bookingInfoModal');
            const userIdElement = document.getElementById('user_id');
            if (userIdElement) {
                window.location.href = `/pay/${userIdElement.value}`;
            }
        };
    }

    document.querySelectorAll(".modal .close").forEach(closeBtn => {
        closeBtn.addEventListener("click", function() {
            const modal = this.closest(".modal");
            if (modal) closeModal(modal.id);
        });
    });

    const defaultLocation = "53.18991001551042,45.01398385569291|ул. Кураева, 10";
    const mapData = initializeMap(defaultLocation);

    const locationSelect = document.getElementById("location");
    if (locationSelect) {
        locationSelect.addEventListener("change", () => updateMap(mapData, locationSelect));
    }

    handleFormSubmission();
});

function loadScheme(address, floor) {
    const parkingSchemeImg = document.getElementById('parkingScheme');
    const noSchemeText = document.getElementById('noSchemeText');
    const scheme = parkingSchemes[address] && parkingSchemes[address][floor] ? parkingSchemes[address][floor] : null;

    console.log(`Loading scheme for Address: ${address}, Floor: ${floor}, Scheme: ${scheme}`);

    if (!scheme) {
        parkingSchemeImg.style.display = 'none';
        noSchemeText.style.display = 'block';
        return;
    }

    fetch(scheme)
        .then(response => {
            if (response.ok) {
                parkingSchemeImg.src = scheme;
                parkingSchemeImg.style.display = 'block';
                noSchemeText.style.display = 'none';
            } else {
                console.warn(`Изображение ${scheme} не найдено`);
                parkingSchemeImg.style.display = 'none';
                noSchemeText.style.display = 'block';
            }
        })
        .catch(error => {
            console.error(`Ошибка загрузки изображения ${scheme}:`, error);
            parkingSchemeImg.style.display = 'none';
            noSchemeText.style.display = 'block';
        });
}

const selectSpotBtn = document.getElementById('selectSpotBtn');
if (selectSpotBtn) {
    selectSpotBtn.addEventListener('click', async () => {
        const locationSelect = document.getElementById('location');
        const location = locationSelect.value;
        const userIdElement = document.getElementById('user_id');

        if (!location) {
            locationSelect.setCustomValidity('Пожалуйста, выберите локацию.');
            locationSelect.reportValidity();
            return;
        } else {
            locationSelect.setCustomValidity('');
        }

        try {
            const response = await fetch(`/api/parking_spots?location=${encodeURIComponent(location)}&user_id=${userIdElement.value}`);
            if (!response.ok) {
                throw new Error(`Ошибка сервера: ${response.status} ${response.statusText}`);
            }
            allSpots = await response.json();
            if (!Array.isArray(allSpots)) {
                throw new Error('Ожидался массив парковочных мест');
            }
            console.log('Загруженные места:', allSpots);

            const spotsTableBody = document.getElementById('spotsTableBody');
            const spotsTableHead = document.querySelector('#spotsList table thead tr');
            spotsTableBody.innerHTML = '';
            spotsTableHead.innerHTML = '';

            const [, address] = location.split('|');
            const hasFloors = allSpots.some(spot => spot.floor !== null && spot.floor !== undefined);

            spotsTableHead.innerHTML = `
                <th>Номер места</th>
                ${hasFloors ? '<th>Этаж</th>' : ''}
                <th>Статус</th>
            `;

            function updateTable(floor) {
                spotsTableBody.innerHTML = '';
                const spots = hasFloors ? allSpots.filter(spot => spot.floor == floor) : allSpots;
                spots.forEach(spot => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${spot.spot_number}</td>
                        ${hasFloors ? `<td>${spot.floor || 'Нет этажа'}</td>` : ''}
                        <td>${spot.is_available ? 'Свободно' : 'Занято'}</td>
                    `;
                    row.dataset.price = spot.price ? spot.price.toFixed(2) : '0.00';
                    if (spot.is_available) {
                        row.classList.add('spot-cell');
                        if (selectedSpot && selectedSpot.spot_number === spot.spot_number && (!hasFloors || selectedSpot.floor == spot.floor)) {
                            row.classList.add('selected');
                        }
                        row.addEventListener('click', () => {
                            document.querySelectorAll('.spot-cell').forEach(cell => cell.classList.remove('selected'));
                            row.classList.add('selected');
                            selectedSpot = spot;
                            document.getElementById('confirmSpotBtn').disabled = false;
                            priceInput.value = spot.price ? `${spot.price.toFixed(2)} (руб.)` : '0.00 (руб.)';
                            console.log(`Выбрано место ${spot.spot_number}, этаж ${spot.floor || 'без этажа'}, цена: ${spot.price}`);
                        });
                    } else {
                        row.classList.add('spot-cell', 'occupied');
                    }
                    spotsTableBody.appendChild(row);
                });
            }

            const galleryControls = document.getElementById('galleryControls');
            const prevFloorBtn = document.getElementById('prevFloorBtn');
            const nextFloorBtn = document.getElementById('nextFloorBtn');
            const currentFloorSpan = document.getElementById('currentFloor');

            if (hasFloors) {
                availableFloors = [...new Set(allSpots.map(spot => spot.floor).filter(f => f !== null))].sort();
                currentFloorIndex = availableFloors.indexOf(availableFloors[0]) || 0;
                galleryControls.style.display = 'flex';
                updateGallery(address);
            } else {
                availableFloors = [];
                currentFloorIndex = 0;
                galleryControls.style.display = 'none';
                loadScheme(address, 'default');
                updateTable(null);
            }

            function updateGallery(address) {
                const floor = availableFloors[currentFloorIndex];
                currentFloorSpan.textContent = `Этаж ${floor}`;
                loadScheme(address, floor);
                prevFloorBtn.disabled = currentFloorIndex === 0;
                nextFloorBtn.disabled = currentFloorIndex === availableFloors.length - 1;
                updateTable(floor);
            }

            prevFloorBtn.onclick = (event) => {
                event.preventDefault();
                if (currentFloorIndex > 0) {
                    currentFloorIndex--;
                    updateGallery(address);
                }
            };

            nextFloorBtn.onclick = (event) => {
                event.preventDefault();
                if (currentFloorIndex < availableFloors.length - 1) {
                    currentFloorIndex++;
                    updateGallery(address);
                }
            };

            showModal('spotModal');
        } catch (error) {
            console.error('Ошибка при загрузке парковочных мест:', error);
            alert(`Не удалось загрузить парковочные места: ${error.message}`);
        }
    });
}

function closeSpotModal() {
    console.log('closeSpotModal called');
    closeModal('spotModal');

    const confirmSpotBtn = document.getElementById('confirmSpotBtn');
    if (confirmSpotBtn) confirmSpotBtn.disabled = true;
    const parkingSchemeImg = document.getElementById('parkingScheme');
    const noSchemeText = document.getElementById('noSchemeText');
    if (parkingSchemeImg) {
        parkingSchemeImg.src = '';
        parkingSchemeImg.style.display = 'none';
    }
    if (noSchemeText) {
        noSchemeText.style.display = 'none';
    }
    if (!document.getElementById('selected_spot').value) {
        selectedSpot = null;
        priceInput.value = 'Выберите место';
    }
}

function showConfirmationModal(message) {
    const confirmationModal = document.getElementById('spotConfirmationModal');
    const confirmationText = document.getElementById('spotConfirmationText');
    if (confirmationModal && confirmationText) {
        confirmationText.textContent = message;
        showModal('spotConfirmationModal');
        setTimeout(() => closeModal('spotConfirmationModal'), 1000);
    }
}

const spotModalCloseBtn = document.querySelector('#spotModal .close');
if (spotModalCloseBtn) {
    spotModalCloseBtn.addEventListener('click', closeSpotModal);
}

const confirmSpotBtn = document.getElementById('confirmSpotBtn');
if (confirmSpotBtn) {
    confirmSpotBtn.addEventListener('click', async () => {
        if (selectedSpot) {
            const selectedSpotInput = document.getElementById('selected_spot');
            const locationSelect = document.getElementById('location');
            const [, address] = locationSelect.value.split('|');

            if (selectedSpotInput) {
                selectedSpotInput.value = selectedSpot.spot_number;
                priceInput.value = selectedSpot.price ? `${selectedSpot.price.toFixed(2)} (руб.)` : '0.00 (руб.)';
                showConfirmationModal(`Выбрано место: №${selectedSpot.spot_number}${selectedSpot.floor ? `, этаж ${selectedSpot.floor}` : ''}`);
                console.log('Подтверждено место:', selectedSpot);
                closeSpotModal();
            }
        }
    });
}

window.addEventListener('click', (event) => {
    if (event.target === document.getElementById('spotModal')) {
        closeSpotModal();
    }
});

async function loadParkingSpots(address) {
    const response = await fetch(`/parking_spots?address=${encodeURIComponent(address)}`);
    const spots = await response.json();
    const hasFloors = spots.some(spot => spot.floor !== null && spot.floor !== undefined);
    
    const floorInput = document.getElementById('floor');
    if (!hasFloors) {
        floorInput.disabled = true; 
        floorInput.value = ''; 
    } else {
        floorInput.disabled = false;
    }
}

async function submitBooking() {
    const bookingData = {
        user_id: parseInt(userIdElement.value),
        address: address.trim(),
        spot_number: parseInt(selectedSpotInput.value),
        start_time: startDatetimeElement.value,
        end_time: endDatetimeElement.value
    };

    const responseSpots = await fetch(`/parking_spots?address=${encodeURIComponent(address)}`);
    const spots = await responseSpots.json();
    const hasFloors = spots.some(spot => spot.floor !== null && spot.floor !== undefined);

    if (hasFloors && floorElement.value !== '' && floorElement.value !== null) {
        bookingData.floor = parseInt(floorElement.value);
    }

    console.log('Отправляемые данные:', bookingData);

    try {
        const response = await fetch('/book', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(bookingData)
        });

        if (response.ok) {
            const data = await response.json();
            if (data && data.booking_id) {
                console.log("Бронирование успешно:", data);
                showBookingInfoModal(data.spot_number, data.amount);
            } else {
                console.error("Сервер вернул пустой или некорректный ответ:", data);
                alert("Бронирование не удалось. Попробуйте снова.");
            }
        } else {
            const errorData = await response.json();
            console.error("Ошибка сервера:", errorData);
            alert(`Ошибка бронирования: ${errorData.detail || 'Неизвестная ошибка'}`);
        }
    } catch (error) {
        console.error("Ошибка при отправке данных:", error);
        alert(`Ошибка при отправке данных: ${error.message}`);
    }
}
