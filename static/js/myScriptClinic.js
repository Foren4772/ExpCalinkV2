document.addEventListener('DOMContentLoaded', () => {
  const userArea = document.getElementById('userArea');
  const usuario = JSON.parse(localStorage.getItem('usuario'));
  const id = window.location.pathname.split('/')[2]; // Simula o `useParams`

  const handleLogout = () => {
    localStorage.removeItem('usuario');
    localStorage.removeItem('token');
    window.location.href = '/';
  };

  // Renderiza a área do usuário
  if (usuario) {
    userArea.innerHTML = `
      <div class="dropdown">
        <button
          class="btn btn-outline-primary dropdown-toggle"
          type="button"
          id="dropdownMenuButton"
          data-bs-toggle="dropdown"
          aria-expanded="false"
        >
          Olá, ${usuario.nome?.split(' ')[0] || 'Usuário'}
        </button>
        <ul class="dropdown-menu" aria-labelledby="dropdownMenuButton">
          <li><a class="dropdown-item" href="/perfil/${id}">Meu Perfil</a></li>
          <li><button class="dropdown-item" id="logoutBtn">Sair</button></li>
        </ul>
      </div>
    `;
    document.getElementById('logoutBtn').addEventListener('click', handleLogout);
  } else {
    userArea.innerHTML = `
      <a class="btn btn-outline-primary me-2" href="/cadastro-usuario">Cadastrar</a>
      <a class="btn btn-primary" href="/login">Entrar</a>
    `;
  }
});




















































// function w3_open() {
//   document.getElementById("mySidebar").style.display = "block";
// }

// function w3_close() {
//   document.getElementById("mySidebar").style.display = "none";
  
// }

// function w3_show_nav(name) {
//   document.getElementById("menuMedico").style.display = "none";
//   document.getElementById(name).style.display = "block";
// }
// function w3_show_none() {
//   document.getElementById("menuMedico").style.display = "none";
// }

// function validaImagem(input) {
//   var caminho = input.value;

//   if (caminho) {
//       var comecoCaminho = (caminho.indexOf('\\') >= 0 ? caminho.lastIndexOf('\\') : caminho.lastIndexOf('/'));
//       var nomeArquivo = caminho.substring(comecoCaminho);

//       if (nomeArquivo.indexOf('\\') === 0 || nomeArquivo.indexOf('/') === 0) {
//           nomeArquivo = nomeArquivo.substring(1);
//       }

//       var extensaoArquivo = nomeArquivo.indexOf('.') < 1 ? '' : nomeArquivo.split('.').pop();

//       if (extensaoArquivo != 'gif' &&
//           extensaoArquivo != 'png' &&
//           extensaoArquivo != 'jpg' &&
//           extensaoArquivo != 'jpeg') {
//           input.value = '';
//           alert("É preciso selecionar um arquivo de imagem (gif, png, jpg ou jpeg)");
//       }
//   } else {
//       input.value = '';
//       alert("Selecione um caminho de arquivo válido");
//   }
//   if (input.files && input.files[0]) {
//       var arquivoTam = input.files[0].size / 1024 / 1024;
//       if (arquivoTam < 16) {
//           var reader = new FileReader();
//           reader.onload = function(e) {
//               document.getElementById('imagemSelecionada').setAttribute('src', e.target.result);
//           };
//           reader.readAsDataURL(input.files[0]);
//       } else {
//           input.value = '';
//           alert("O arquivo precisa ser uma imagem com menos de 16 MB");
//       }
//   } else{
//       document.getElementById('imagemSelecionada').setAttribute('src', '#');
//   }
// }

// // Script para mostrar ou ocultar senha
// function mostrarOcultarSenhaLogin() {
//   var senha  = document.getElementById("Senha");

//   if (senha.type == "password"){
//     senha.type  = "text";
//   } else {
//     senha.type  = "password";
//   }
// }

// // Script para mostrar ou ocultar senha
// function mostrarOcultarSenhaCadastro() {
//   var senha1 = document.getElementById("Senha1");
//   var senha2 = document.getElementById("Senha2");

//   if (senha1.type == "password"){
//     senha1.type = "text";
//     senha2.type = "text";
//   } else {
//     senha1.type = "password";
//     senha2.type = "password";
//   }
// }

// // Script para validar confirmação de senha Ok
// function validarSenha() {
//   var senha  = document.getElementById("Senha1");
//   var senha2 = document.getElementById("Senha2");

//   if (senha.value != senha2.value) {
//     senha2.setCustomValidity("Senhas diferentes!");
//     senha2.reportValidity();
//     return false;
//   } else {
//     senha2.setCustomValidity("");
//     return true;
//   }
// }

// // Script para preenchimento de número de celular
// function mask(o, f) {
//   setTimeout(function() {
//     var v = mphone(o.value);
//     if (v != o.value) {
//       o.value = v;
//     }
//   }, 1);
// }


// function mphone(v) {
//   var r = v.replace(/\D/g, "");
//   r = r.replace(/^0/, "");
//   if (r.length > 10) {
//     r = r.replace(/^(\d\d)(\d{5})(\d{4}).*/, "($1)$2-$3");
//   } else if (r.length > 5) {
//     r = r.replace(/^(\d\d)(\d{4})(\d{0,4}).*/, "($1)$2-$3");
//   } else if (r.length > 2) {
//     r = r.replace(/^(\d\d)(\d{0,5})/, "($1)$2");
//   } else {
//     r = r.replace(/^(\d*)/, "($1");
//   }
//   return r;
// }

// function mensagem(m) {
//   alert(m);
// }