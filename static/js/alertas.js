// alertas.js
function mostrarAlerta(tipo, mensagem) {
    switch (tipo) {
        case "sucesso":
            Swal.fire({
                icon: 'success',
                title: 'Sucesso!',
                text: mensagem,
                confirmButtonColor: '#1a1a1a',
                confirmButtonText: 'Fechar'
            });
            break;

        case "erro":
            Swal.fire({
                icon: 'error',
                title: 'Erro!',
                text: mensagem,
                confirmButtonColor: '#1a1a1a',
                confirmButtonText: 'Fechar'
            });
            break;

        case "info":
            Swal.fire({
                icon: 'info',
                title: 'Atenção',
                text: mensagem,
                confirmButtonColor: '#1a1a1a',
                confirmButtonText: 'Fechar'
            });
            break;

        default:
            console.warn("Tipo de alerta desconhecido:", tipo);
    }
}
