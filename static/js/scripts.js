// /static/js/scripts.js

document.addEventListener('DOMContentLoaded', function () {
    // Tenta encontrar o formulário de login. Se não existir, sai da função.
    const loginForm = document.getElementById('loginForm');
    if (!loginForm) {
        // console.log("Formulário de login não encontrado nesta página. O script não será executado.");
        return; // Sai da função se o formulário não for encontrado
    }

    loginForm.addEventListener('submit', function (e) {
        // Validações básicas no frontend
        const login = document.getElementById('Login'); // Obtenha o elemento
        const senha = document.getElementById('Senha'); // Obtenha o elemento
        let isValid = true;

        // Limpa erros anteriores
        if (login) login.classList.remove('is-invalid'); // Verifica se o elemento existe
        if (senha) senha.classList.remove('is-invalid'); // Verifica se o elemento existe

        const loginError = document.getElementById('loginError');
        const senhaError = document.getElementById('senhaError');

        if (loginError) loginError.textContent = ''; // Limpa mensagens de erro anteriores
        if (senhaError) senhaError.textContent = ''; // Limpa mensagens de erro anteriores


        // Validação de campos (garantindo que os elementos existem antes de acessar .value)
        if (!login || !login.value.trim()) {
            if (login) login.classList.add('is-invalid');
            if (loginError) loginError.textContent = 'Login é obrigatório';
            isValid = false;
        }

        if (!senha || !senha.value.trim()) {
            if (senha) senha.classList.add('is-invalid');
            if (senhaError) senhaError.textContent = 'Senha é obrigatória';
            isValid = false;
        } else if (senha.value.length < 6) {
            if (senha) senha.classList.add('is-invalid');
            if (senhaError) senhaError.textContent = 'Senha deve ter pelo menos 6 caracteres';
            isValid = false;
        }

        if (!isValid) {
            e.preventDefault();
            Swal.fire({
                icon: 'error',
                title: 'Formulário inválido',
                text: 'Por favor, preencha todos os campos corretamente',
                confirmButtonColor: '#303030'
            });
        }
        // Se válido, o formulário será submetido normalmente ao backend
    });
}); // Fim do DOMContentLoaded