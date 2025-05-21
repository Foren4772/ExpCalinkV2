// /static/js/alertas.js

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

        case "error": // Alterado de "erro" para "error"
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

        case "warning": // Adicionado/Corrigido para usar 'html'
            Swal.fire({
                icon: 'warning',
                title: 'Atenção!',
                html: 'mensagem', // <-- IMPORTANTE: usar 'html' para mensagens com tags como <ul><li>
                confirmButtonColor: '#1a1a1a',
                confirmButtonText: 'OK'
            });
            break;

        default:
            console.warn("Tipo de alerta desconhecido:", tipo);
    }
}