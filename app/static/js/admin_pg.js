document.addEventListener("DOMContentLoaded", () => {
    if (localStorage.getItem('reloadAfterBooking')) {
        console.log('Обнаружен флаг reloadAfterBooking, перезагружаем страницу');
        localStorage.removeItem('reloadAfterBooking');
        location.reload();
    }

    const parkingSelect = document.getElementById("parking-select");
    const floorButtonsContainer = document.getElementById("floor-buttons");
    const spotsTablesContainer = document.getElementById("spots-tables");
    const notification = document.getElementById("notification");
    const usersTableBody = document.getElementById("users-table-body");
    const bookingsModal = document.getElementById("bookingsModal");
    const bookingsTableBody = document.getElementById("bookings-table-body");
    const refreshUsersBtn = document.getElementById("refresh-users-btn");
    const startDateInput = document.getElementById("start-date");
    const endDateInput = document.getElementById("end-date");
    const parkingsChartCanvas = document.getElementById("parkings-chart");
    const spotsChartCanvas = document.getElementById("spots-chart");
    const revenueChartCanvas = document.getElementById("revenue-chart");

    if (!parkingSelect || !floorButtonsContainer || !spotsTablesContainer || !notification || 
        !usersTableBody || !bookingsModal || !bookingsTableBody || !refreshUsersBtn || 
        !startDateInput || !endDateInput || 
        !parkingsChartCanvas || !spotsChartCanvas || !revenueChartCanvas) {
        console.error("Ошибка: Не найдены необходимые элементы DOM", {
            parkingSelect: !!parkingSelect,
            floorButtonsContainer: !!floorButtonsContainer,
            spotsTablesContainer: !!spotsTablesContainer,
            notification: !!notification,
            usersTableBody: !!usersTableBody,
            bookingsModal: !!bookingsModal,
            bookingsTableBody: !!bookingsTableBody,
            refreshUsersBtn: !!refreshUsersBtn,
            startDateInput: !!startDateInput,
            endDateInput: !!endDateInput,
            parkingsChartCanvas: !!parkingsChartCanvas,
            spotsChartCanvas: !!spotsChartCanvas,
            revenueChartCanvas: !!revenueChartCanvas
        });
        return;
    }

    function showNotification(message) {
        notification.textContent = message;
        notification.style.display = "block";
        setTimeout(() => {
            notification.style.display = "none";
        }, 2000);
    }

    const tabLinks = document.querySelectorAll(".tab-link");
    const tabContents = document.querySelectorAll(".tab-content");

    let parkingsChart, spotsChart, revenueChart;

    tabLinks.forEach(link => {
        link.addEventListener("click", () => {
            tabLinks.forEach(l => l.classList.remove("active"));
            tabContents.forEach(c => c.classList.remove("active"));
            link.classList.add("active");
            document.getElementById(`${link.dataset.tab}-tab`).classList.add("active");

            if (link.dataset.tab === "users") {
                loadUsers();
            } else if (link.dataset.tab === "analytics") {
                loadAnalytics();
            }
        });
    });

    refreshUsersBtn.addEventListener("click", () => {
        console.log("Клик по кнопке обновления пользователей");
        loadUsers();
        showNotification("Таблица пользователей обновлена");
    });

    startDateInput.addEventListener("change", () => {
        if (startDateInput.value && endDateInput.value) {
            console.log("Выбраны даты:", startDateInput.value, endDateInput.value);
            loadAnalytics();
        }
    });

    endDateInput.addEventListener("change", () => {
        if (startDateInput.value && endDateInput.value) {
            console.log("Выбраны даты:", startDateInput.value, endDateInput.value);
            loadAnalytics();
        }
    });

    async function loadUsers() {
        try {
            const token = getCookie("access_token");
            console.log("Токен для запроса пользователей:", token);
            const response = await fetch("/admin/users", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!response.ok) {
                throw new Error(await response.text());
            }
            const users = await response.json();
            console.log("Получены данные пользователей:", users);
            renderUsers(users);
        } catch (error) {
            console.error("Ошибка при загрузке пользователей:", error);
            showNotification(`Ошибка: ${error.message}`);
        }
    }

    function renderUsers(users) {
        usersTableBody.innerHTML = "";
        const filteredUsers = users.filter(user => user.RoleName !== 'Admin');
        if (filteredUsers.length === 0) {
            const row = document.createElement("tr");
            row.innerHTML = `<td colspan="4">Нет пользователей</td>`;
            usersTableBody.appendChild(row);
            return;
        }
        filteredUsers.forEach(user => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${user.Username}</td>
                <td>${user.Email}</td>
                <td>${user.Status === 'White' ? 'Белый список' : 'Черный список'}</td>
                <td>
                    <button class="action-btn view-bookings-btn" data-user-id="${user.UserID}">Просмотреть бронирования</button>
                    ${
                        user.Status === 'White'
                            ? `<button class="action-btn blacklist-btn" data-user-id="${user.UserID}">Внести в черный список</button>`
                            : `<button class="action-btn whitelist-btn" data-user-id="${user.UserID}">Внести в белый список</button>`
                    }
                </td>
            `;
            usersTableBody.appendChild(row);
        });

        document.querySelectorAll(".view-bookings-btn").forEach(button => {
            button.addEventListener("click", () => {
                const userId = button.dataset.userId;
                loadUserBookings(userId);
            });
        });

        document.querySelectorAll(".blacklist-btn").forEach(button => {
            button.addEventListener("click", async () => {
                const userId = button.dataset.userId;
                try {
                    const token = getCookie("access_token");
                    const response = await fetch(`/admin/users/${userId}/status`, {
                        method: "POST",
                        headers: {
                            "Authorization": `Bearer ${token}`,
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({ status: "Black" })
                    });
                    if (!response.ok) {
                        throw new Error(await response.text());
                    }
                    await response.json();
                    showNotification("Статус пользователя обновлен");
                    loadUsers();
                } catch (error) {
                    console.error("Ошибка при внесении в черный список:", error);
                    showNotification(`Ошибка: ${error.message}`);
                }
            });
        });

        document.querySelectorAll(".whitelist-btn").forEach(button => {
            button.addEventListener("click", async () => {
                const userId = button.dataset.userId;
                try {
                    const token = getCookie("access_token");
                    const response = await fetch(`/admin/users/${userId}/status`, {
                        method: "POST",
                        headers: {
                            "Authorization": `Bearer ${token}`,
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({ status: "White" })
                    });
                    if (!response.ok) {
                        throw new Error(await response.text());
                    }
                    await response.json();
                    showNotification("Статус пользователя обновлен");
                    loadUsers();
                } catch (error) {
                    console.error("Ошибка при внесении в белый список:", error);
                    showNotification(`Ошибка: ${error.message}`);
                }
            });
        });
    }

    async function loadUserBookings(userId) {
        try {
            const token = getCookie("access_token");
            console.log(`Токен для запроса бронирований userId=${userId}:`, token);
            const response = await fetch(`/admin/users/${userId}/bookings`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!response.ok) {
                throw new Error(await response.text());
            }
            const bookings = await response.json();
            console.log("Получены бронирования:", bookings);
            renderBookings(bookings);
            showModal("bookingsModal");
        } catch (error) {
            console.error("Ошибка при загрузке бронирований:", error);
            showNotification(`Ошибка: ${error.message}`);
        }
    }

    function renderBookings(bookings) {
        bookingsTableBody.innerHTML = "";
        if (bookings.length === 0) {
            const row = document.createElement("tr");
            row.innerHTML = `<td colspan="7">Нет бронирований</td>`;
            bookingsTableBody.appendChild(row);
            return;
        }
        bookings.forEach(booking => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${booking.bookingId}</td>
                <td>${booking.address}</td>
                <td>${booking.floor || '-'}</td>
                <td>${new Date(booking.startTime).toLocaleString()}</td>
                <td>${new Date(booking.endTime).toLocaleString()}</td>
                <td>${booking.carBrand || '-'}</td>
                <td>${booking.carNumber || '-'}</td>
            `;
            bookingsTableBody.appendChild(row);
        });
    }

    async function loadAnalytics() {
        const startDate = startDateInput.value;
        const endDate = endDateInput.value;
        const token = getCookie("access_token");
        console.log(`Загрузка аналитики: startDate=${startDate}, endDate=${endDate}, токен:`, token);

        if (!startDate || !endDate) {
            showNotification("Пожалуйста, выберите обе даты");
            return;
        }

        try {
            const urlParams = `start_date=${startDate}T00:00:00&end_date=${endDate}T23:59:59`;

            const parkingsResponse = await fetch(`/admin/analytics/parkings?${urlParams}`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!parkingsResponse.ok) {
                throw new Error(await parkingsResponse.text());
            }
            const parkingsData = await parkingsResponse.json();
            console.log("Получена аналитика парковок:", parkingsData);
            renderParkingsChart(parkingsData);

            const spotsResponse = await fetch(`/admin/analytics/spots?${urlParams}`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!spotsResponse.ok) {
                throw new Error(await spotsResponse.text());
            }
            const spotsData = await spotsResponse.json();
            console.log("Получена аналитика мест:", spotsData);
            renderSpotsChart(spotsData);

            const revenueResponse = await fetch(`/admin/analytics/revenue?${urlParams}`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!revenueResponse.ok) {
                throw new Error(await revenueResponse.text());
            }
            const revenueData = await revenueResponse.json();
            console.log("Получена аналитика доходов:", revenueData);
            renderRevenueChart(revenueData);

        } catch (error) {
            console.error("Ошибка при загрузке аналитики:", error);
            showNotification(`Ошибка: ${error.message}`);
        }
    }

    function renderParkingsChart(data) {
        if (parkingsChart) {
            parkingsChart.destroy();
        }
        parkingsChart = new Chart(parkingsChartCanvas, {
            type: 'bar',
            data: {
                labels: data.map(item => item.address),
                datasets: [{
                    label: 'Количество бронирований',
                    data: data.map(item => item.booking_count),
                    backgroundColor: '#3498db',
                    borderColor: '#2980b9',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Количество бронирований'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Парковка'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    function renderSpotsChart(data) {
        if (spotsChart) {
            spotsChart.destroy();
        }
        const labels = data.map(item => `${item.spot_number} (${item.address}${item.floor ? ', эт. ' + item.floor : ''})`);
        spotsChart = new Chart(spotsChartCanvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Среднее время бронирования (часы)',
                    data: data.map(item => item.avg_hours),
                    backgroundColor: '#2ecc71',
                    borderColor: '#27ae60',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Среднее время (часы)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Место'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    function renderRevenueChart(data) {
        if (revenueChart) {
            revenueChart.destroy();
        }

        const dates = [...new Set(data.map(item => item.date))].sort();
        const addresses = [...new Set(data.map(item => item.address))];
        
        const datasets = addresses.map(address => {
            const addressData = data.filter(item => item.address === address);
            return {
                label: address,
                data: dates.map(date => {
                    const entry = addressData.find(item => item.date === date);
                    return entry ? entry.revenue : 0;
                }),
                backgroundColor: getRandomColor(),
                borderColor: getRandomColor(),
                borderWidth: 1
            };
        });

        revenueChart = new Chart(revenueChartCanvas, {
            type: 'bar',
            data: {
                labels: dates,
                datasets: datasets
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Доход (руб.)'
                        },
                        stacked: false 
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Дата'
                        },
                        stacked: false 
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + context.parsed.y.toFixed(2) + ' руб.';
                            }
                        }
                    }
                }
            }
        });
    }

    function getRandomColor() {
        const letters = '0123456789ABCDEF';
        let color = '#';
        for (let i = 0; i < 6; i++) {
            color += letters[Math.floor(Math.random() * 16)];
        }
        return color;
    }

    function showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add("show");
        }
    }

    function closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove("show");
        }
    }


    bookingsModal.querySelector(".close").addEventListener("click", () => {
        closeModal("bookingsModal");
    });

    parkingSelect.addEventListener("change", async () => {
        const locationId = parkingSelect.value;
        if (!locationId) {
            floorButtonsContainer.innerHTML = "";
            spotsTablesContainer.innerHTML = "";
            return;
        }

        try {
            const token = getCookie("access_token");
            console.log("Токен для запроса:", token);
            const response = await fetch(`/admin/spots/${locationId}`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!response.ok) {
                throw new Error(await response.text());
            }
            const data = await response.json();
            console.log("Получены данные:", data);
            renderFloors(data.floors, data.spots);
        } catch (error) {
            console.error("Ошибка при загрузке мест:", error);
            showNotification(`Ошибка: ${error.message}`);
        }
    });

    function renderFloors(floors, spots) {
        floorButtonsContainer.innerHTML = "";
        spotsTablesContainer.innerHTML = "";

        const uniqueFloors = floors.filter(f => f !== null);
        if (uniqueFloors.length <= 1) {
            renderTable(spots, null);
            return;
        }

        floors.forEach(floor => {
            const button = document.createElement("button");
            button.className = "floor-btn";
            button.textContent = floor !== null ? `Этаж ${floor}` : "Без этажа";
            button.dataset.floor = floor !== null ? floor : "null";
            button.addEventListener("click", () => {
                document.querySelectorAll(".floor-btn").forEach(btn => btn.classList.remove("active"));
                button.classList.add("active");
                renderTable(spots.filter(spot => spot.Floor === floor || (floor === null && spot.Floor === null)), floor);
            });
            floorButtonsContainer.appendChild(button);
        });

        const firstButton = floorButtonsContainer.querySelector(".floor-btn");
        if (firstButton) {
            firstButton.classList.add("active");
            const firstFloor = firstButton.dataset.floor === "null" ? null : firstButton.dataset.floor;
            renderTable(spots.filter(spot => spot.Floor === firstFloor || (firstFloor === null && spot.Floor === null)), firstFloor);
        }
    }

    function renderTable(spots, floor) {
        spotsTablesContainer.innerHTML = "";
        const table = document.createElement("table");
        table.className = "spots-table";

        const thead = document.createElement("thead");
        const headerRow = document.createElement("tr");
        headerRow.innerHTML = `
            <th>Номер места</th>
            ${floor !== null ? '<th>Этаж</th>' : ''}
            <th>Цена (руб.)</th>
            <th>Статус</th>
            <th>Действия</th>
        `;
        thead.appendChild(headerRow);
        table.appendChild(thead);

        const tbody = document.createElement("tbody");
        spots.forEach(spot => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${spot.SpotNumber}</td>
                ${floor !== null ? `<td>${spot.Floor || '-'}</td>` : ''}
                <td>
                    <span class="price-display" data-spot-id="${spot.SpotID}">${spot.Price.toFixed(2)}</span>
                    <div class="price-edit" style="display: none;">
                        <input type="number" min="0" step="0.01" value="${spot.Price.toFixed(2)}" class="price-input">
                        <button class="save-price-btn">Сохранить</button>
                    </div>
                </td>
                <td>${spot.IsAvailable ? 'Свободно' : 'Зарезервировано'}</td>
                <td>
                    <button class="action-btn" onclick="manageSpot(${spot.SpotID}, 'reserve')" ${!spot.IsAvailable ? 'disabled' : ''}>Зарезервировать</button>
                    <button class="action-btn" onclick="manageSpot(${spot.SpotID}, 'free')" ${spot.IsAvailable ? 'disabled' : ''}>Освободить</button>
                </td>
            `;
            tbody.appendChild(row);
        });
        table.appendChild(tbody);

        spotsTablesContainer.appendChild(table);

        document.querySelectorAll(".price-display").forEach(display => {
            display.addEventListener("click", () => {
                const editDiv = display.nextElementSibling;
                display.style.display = "none";
                editDiv.style.display = "inline-flex";
            });
        });

        document.querySelectorAll(".save-price-btn").forEach(button => {
            button.addEventListener("click", async () => {
                const editDiv = button.parentElement;
                const input = editDiv.querySelector(".price-input");
                const display = editDiv.previousElementSibling;
                const spotId = display.dataset.spotId;
                const newPrice = parseFloat(input.value);

                if (isNaN(newPrice) || newPrice < 0) {
                    showNotification("Пожалуйста, введите корректную цену");
                    return;
                }

                try {
                    const token = getCookie("access_token");
                    console.log(`Токен для изменения цены SpotID=${spotId}:`, token);
                    const response = await fetch(`/admin/spots/${spotId}/update_price`, {
                        method: "POST",
                        headers: {
                            "Authorization": `Bearer ${token}`,
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({ price: newPrice })
                    });

                    if (!response.ok) {
                        throw new Error(await response.text());
                    }

                    const result = await response.json();
                    showNotification(result.message);
                    display.textContent = newPrice.toFixed(2);
                    display.style.display = "inline";
                    editDiv.style.display = "none";
                    parkingSelect.dispatchEvent(new Event("change"));
                } catch (error) {
                    console.error("Ошибка при изменении цены:", error);
                    showNotification(`Ошибка: ${error.message}`);
                }
            });
        });
    }

    window.manageSpot = async (spotId, action) => {
        try {
            const token = getCookie("access_token");
            const response = await fetch(`/admin/spots/${spotId}/${action}`, {
                method: "POST",
                headers: { 
                    "Authorization": `Bearer ${token}`,
                    "Content-Type": "application/json"
                }
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Неизвестная ошибка сервера");
            }
            
            const result = await response.json();
            showNotification(result.message);
            parkingSelect.dispatchEvent(new Event("change"));
        } catch (error) {
            console.error(`Ошибка при ${action}:`, error);
            showNotification(`Ошибка: ${error.message}`);
        }
    };

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }
});

const cancellationModal = document.getElementById('cancellationModal');
if (cancellationModal) {
    const closeCancellationModal = cancellationModal.querySelector('.close');
    if (closeCancellationModal) {
        closeCancellationModal.addEventListener('click', () => {
            cancellationModal.classList.remove('show');
            cancellationModal.classList.add('hide');
        });
    }

    window.addEventListener('click', (event) => {
        if (event.target === cancellationModal) {
            cancellationModal.classList.remove('show');
            cancellationModal.classList.add('hide');
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const cancellationModal = document.getElementById('cancellationModal');
    if (cancellationModal && cancellationModal.classList.contains('show')) {
        cancellationModal.style.display = 'block';
    }
});