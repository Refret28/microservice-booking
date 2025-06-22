document.addEventListener("DOMContentLoaded", () => {
    console.log("register.js загружен успешно");

    const loginForm = document.getElementById("login-form");
    const registerForm = document.getElementById("register-form");

    const notification = document.getElementById('authErrorNotification');
    if (!notification) {
        console.error("Элемент authErrorNotification не найден в DOM");
    } else {
        console.log("Элемент authErrorNotification найден");
    }

    function showAuthErrorNotification(message) {
        console.log('Вызов showAuthErrorNotification:', message);
        if (!notification) {
            console.error('Уведомление authErrorNotification не найдено');
            return;
        }
        notification.textContent = message;
        notification.classList.remove('hide');
        notification.classList.add('show');
        setTimeout(() => {
            notification.classList.remove('show');
            notification.classList.add('hide');
            console.log('Уведомление скрыто');
        }, 5000); 
    }

    const closeBtn = document.querySelector('#authErrorNotification .close');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            notification.classList.remove('show');
            notification.classList.add('hide');
            console.log('Уведомление закрыто пользователем');
        });
    } else {
        console.warn("Кнопка закрытия уведомления не найдена");
    }

    if (!registerForm) {
        console.log("Форма регистрации не найдена, это страница логина");
    } else {
        console.log("Форма регистрации найдена:", registerForm);
    }

    if (registerForm) {
        registerForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            console.log("Событие submit перехвачено для формы регистрации");

            const username = document.getElementById("username").value;
            const email = document.getElementById("email").value;
            const phone = document.getElementById("phone").value;
            const password = document.getElementById("password").value;

            console.log("Данные формы:", { username, email, phone, password });

            if (password.length < 3) {
                showAuthErrorNotification("Пароль должен содержать минимум 3 символов");
                return;
            }

            try {
                console.log("Отправка POST-запроса на /register");
                const response = await fetch("/register", {
                    method: "POST",
                    headers: { "Content-Type": "application/x-www-form-urlencoded" },
                    body: new URLSearchParams({ username, email, phone, password })
                });

                console.log("Ответ сервера:", response.status, response.redirected ? response.url : "");

                if (response.redirected) {
                    console.log("Редирект на:", response.url);
                    window.location.href = response.url;
                    return;
                }

                if (!response.ok) {
                    let errorData;
                    try {
                        errorData = await response.json();
                        console.log("Данные ошибки:", errorData);
                    } catch (e) {
                        console.error("Ошибка разбора JSON:", e);
                        errorData = { detail: "Ошибка сервера" };
                    }
                    showAuthErrorNotification(errorData.detail || "Ошибка при регистрации");
                }
            } catch (error) {
                console.error("Ошибка при отправке запроса:", error);
                showAuthErrorNotification("Произошла ошибка. Попробуйте снова.");
            }
        });
    }

    if (loginForm) {
        loginForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            console.log("Событие submit перехвачено для формы логина");

            const email = document.getElementById("modal-email").value;
            const password = document.getElementById("modal-password").value;

            try {
                console.log("Отправка POST-запроса на /login");
                const response = await fetch("/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/x-www-form-urlencoded" },
                    body: new URLSearchParams({ username: email, password })
                });

                console.log("Ответ сервера:", {
                    status: response.status,
                    statusText: response.statusText,
                    redirected: response.redirected,
                    url: response.url
                });

                if (response.redirected) {
                    console.log("Редирект на:", response.url);
                    window.location.href = response.url;
                    return;
                }

                if (!response.ok) {
                    let errorData;
                    try {
                        errorData = await response.json();
                        console.log("Данные ошибки:", errorData);
                    } catch (e) {
                        console.error("Ошибка разбора JSON:", e);
                        errorData = { detail: "Ошибка сервера" };
                    }
                    showAuthErrorNotification(errorData.detail || "Ошибка авторизации! Попробуйте еще раз.");
                } else {
                    console.warn("Ответ сервера успешен, но редирект не произошел:", response.status);
                    showAuthErrorNotification("Ошибка авторизации! Попробуйте еще раз.");
                }
            } catch (error) {
                console.error("Ошибка при авторизации:", error);
                showAuthErrorNotification("Ошибка соединения с сервером");
            }
        });
    }
});