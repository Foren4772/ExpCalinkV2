document.getElementById('loginForm').addEventListener('submit', function (e) {
    // Validações básicas no frontend
    const login = document.getElementById('Login').value.trim();
    const senha = document.getElementById('Senha').value.trim();
    let isValid = true;

    // Limpa erros anteriores
    document.getElementById('Login').classList.remove('is-invalid');
    document.getElementById('Senha').classList.remove('is-invalid');

    // Validação de campos
    if (!login) {
        document.getElementById('Login').classList.add('is-invalid');
        document.getElementById('loginError').textContent = 'Login é obrigatório';
        isValid = false;
    }

    if (!senha) {
        document.getElementById('Senha').classList.add('is-invalid');
        document.getElementById('senhaError').textContent = 'Senha é obrigatória';
        isValid = false;
    } else if (senha.length < 6) {
        document.getElementById('Senha').classList.add('is-invalid');
        document.getElementById('senhaError').textContent = 'Senha deve ter pelo menos 6 caracteres';
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