    // --- MÁSCARAS DE ENTRADA ---

    // Mascara para nome: apenas letras e espaços, limite de 100 caracteres
    function MascaraNome (input) {
        let valor = input.value;
        valor = valor.replace(/[^a-zA-ZÀ-ÿ\s]/g, "");
        input.value = valor.slice(0, 100);
    }

    // Mascara para nome da empresa: apenas letras e espaços, limite de 100 caracteres
    function MascaraNome_empresa (input) {
        let valor = input.value;
        valor = valor.replace(/[^a-zA-ZÀ-ÿ\s]/g, "");
        input.value = valor.slice(0, 100);
    }


    // Mascara para chave de acesso: apenas números, limite de 8 caracteres
    function mascaraChavedeAcesso(input) {
        let valor = input.value.replace(/\D/g, "");
        input.value = valor.slice(0, 8);
    }

    // Mascara para email: caracteres válidos em minúsculas
    function mascaraEmail(input) {
        let valor = input.value.replace(/[^a-zA-Z0-9@._-]/g, "");
        input.value = valor.toLowerCase().slice(0, 100);
    }

    // Mascara para CPF: 000.000.000-00
    function mascaraCPF(input) {
        let valor = input.value.replace(/\D/g, "").slice(0, 11);
        valor = valor.replace(/(\d{3})(\d)/, "$1.$2");
        valor = valor.replace(/(\d{3})(\d)/, "$1.$2");
        valor = valor.replace(/(\d{3})(\d{1,2})$/, "$1-$2");
        input.value = valor;
    }

    // Mascara para telefone: (00) 00000-0000
    function mascaraTelefone(input) {
        let valor = input.value.replace(/\D/g, "").slice(0, 11);
        valor = valor.replace(/(\d{2})(\d)/, "($1) $2");
        valor = valor.replace(/(\d{5})(\d)/, "$1-$2"); 
        input.value = valor;
    }

    // Mascara para CNPJ: 00.000.000/0000-00
    function mascaraCNPJ(input) {
        let valor = input.value.replace(/\D/g, "").slice(0, 14);
        valor = valor.replace(/^(\d{2})(\d)/, "$1.$2");
        valor = valor.replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3");
        valor = valor.replace(/\.(\d{3})(\d)/, ".$1/$2");
        valor = valor.replace(/(\d{4})(\d{1,2})$/, "$1-$2");
        input.value = valor;
    }

    // Mascara para CEP: 00000-000
    function mascaraCEP(input) {
        let valor = input.value.replace(/\D/g, "").slice(0, 8);
        valor = valor.replace(/^(\d{5})(\d)/, "$1-$2");
        input.value = valor;
    }
    // --- VALIDAÇÕES ---

    function senhaForte(input) {
        let regex = /^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[^a-zA-Z0-9]).{8,}$/;
        if (!regex.test(input.value)) {
            input.setCustomValidity("A senha deve conter pelo menos 8 caracteres, incluindo maiúsculas, minúsculas, números e símbolos.");
        } else {
            input.setCustomValidity("");
        }
    }

    function confirmarSenha() {
        const senha = document.getElementById("senha");
        const confirmar = document.getElementById("confirmarSenha");
        const erro = document.getElementById("erro-confirmar-senha");

        if (!confirmar || !senha) return true;

        erro.textContent = "";
        confirmar.style.borderColor = "";

        if (confirmar.value !== senha.value) {
            erro.textContent = "As senhas não coincidem.";
            confirmar.style.borderColor = "red";
            return false;
        }
        return true;
    }

    function validarCampo(campo) {
        const input = document.getElementById(campo.id);
        const erro = document.getElementById("erro-" + campo.id);
        if (!input || !erro) return true;

        let valor = input.value.trim();
        if (campo.tipo === 'numero') valor = valor.replace(/\D/g, "");

        erro.textContent = "";
        input.style.borderColor = "";

        if (valor === "") {
            erro.textContent = `${campo.nome} é obrigatório.`;
            input.style.borderColor = "red";
            return false;
        }

        if (valor.length < campo.min) {
            erro.textContent = `${campo.nome} inválido ou incompleto.`;
            input.style.borderColor = "red";
            return false;
        }
        return true;
    }

    // --- CONFIGURAÇÃO E EVENTOS ---

    const campos = [
        { id: 'nome', nome: 'Nome', min: 3, tipo: 'texto' },
        { id: 'cpf', nome: 'CPF', min: 11, tipo: 'numero' },
        { id: 'email', nome: 'E-mail', min: 5, tipo: 'texto' },
        { id: 'telefone', nome: 'Telefone', min: 11, tipo: 'numero' },
        { id: 'senha', nome: 'Senha', min: 8, tipo: 'texto' },
        { id: 'confirmarSenha', nome: 'Confirmar Senha', min: 8, tipo: 'texto' },
        // Campos adicionais para empresa
        { id: 'nome_empresa', nome: 'Nome da Empresa', min: 3, tipo: 'texto' },
        { id: 'cnpj', nome: 'CNPJ', min: 14, tipo: 'numero' },
        { id: 'cep', nome: 'CEP', min: 8, tipo: 'numero' },
        { id: 'logradouro', nome: 'Logradouro', min: 3, tipo: 'texto' },
        { id: 'bairro', nome: 'Bairro', min: 2, tipo: 'texto' },
        { id: 'cidade', nome: 'Cidade', min: 2, tipo: 'texto' },
        { id: 'numero', nome: 'Número', min: 1, tipo: 'texto' }
    ];

    document.addEventListener("DOMContentLoaded", () => {
        // Validação em tempo real para campos existentes
        campos.forEach(campo => {
            const input = document.getElementById(campo.id);
            if (input) {
                input.addEventListener("input", () => {
                    validarCampo(campo);
                    if (campo.id === "senha") {
                        senhaForte(input);
                        const erroSenha = document.getElementById("erro-senha");
                        if (erroSenha) {
                            erroSenha.textContent = input.validationMessage;
                            input.style.borderColor = !input.checkValidity() ? "red" : "";
                        }
                        confirmarSenha();
                    }
                });
            }
        });

        const inputCep = document.getElementById("cep");
        const btnPreencherEndereco = document.getElementById("btnPreencherEndereco");

        if (btnPreencherEndereco) {
            btnPreencherEndereco.addEventListener("click", () => {
                const cep = inputCep ? inputCep.value.replace(/\D/g, "") : "";
                const erroCep = document.getElementById("erro-cep");

                if (cep.length !== 8) {
                    erroCep.textContent = "Informe um CEP válido antes de preencher.";
                    erroCep.style.color = "red";
                    if (inputCep) inputCep.style.borderColor = "red";
                    return;
                }

                erroCep.textContent = "Buscando endereço...";
                erroCep.style.color = "#d4af37";

                fetch(`https://viacep.com.br/ws/${cep}/json/`)
                    .then(response => response.json())
                    .then(dados => {
                        if (dados.erro) {
                            erroCep.textContent = "CEP não encontrado.";
                            erroCep.style.color = "red";
                            if (inputCep) inputCep.style.borderColor = "red";
                            limparCamposEndereco();
                        } else {
                            erroCep.textContent = "";
                            if (inputCep) inputCep.style.borderColor = "";

                            document.getElementById("logradouro").value = dados.logradouro || "";
                            document.getElementById("bairro").value = dados.bairro || "";
                            document.getElementById("cidade").value = `${dados.localidade || ""} - ${dados.uf || ""}`.trim();

                            atualizarEnderecoCompleto();

                            campos.forEach(c => {
                                if (['logradouro', 'bairro', 'cidade'].includes(c.id)) {
                                    validarCampo(c);
                                }
                            });

                            const inputNumero = document.getElementById("numero");
                            if (inputNumero) inputNumero.focus();
                        }
                    })
                    .catch(() => {
                        erroCep.textContent = "Erro ao buscar o CEP. Tente novamente.";
                        erroCep.style.color = "red";
                    });
            });
        }

        const inputNumero = document.getElementById("numero");
        if (inputNumero) {
            inputNumero.addEventListener("input", atualizarEnderecoCompleto);
        }

        const inputConfirmar = document.getElementById("confirmarSenha");
        if (inputConfirmar) inputConfirmar.addEventListener("input", confirmarSenha);

        const formsParaValidar = [
            document.getElementById("cadastro"),
            document.getElementById("formEmpresa")
        ].filter(Boolean);

        formsParaValidar.forEach(form => {
            form.addEventListener("submit", (event) => {
                atualizarEnderecoCompleto();
                let formValido = true;
                campos.forEach(campo => {
                    if (!validarCampo(campo)) formValido = false;
                });
                if (!confirmarSenha()) formValido = false;
                if (!formValido) event.preventDefault();
            });
        });

        // Impedir espaços na senha
        const inputSenha = document.getElementById('senha');
        if (inputSenha) {
            inputSenha.addEventListener('input', function() {
                this.value = this.value.replace(/\s/g, '');
            });
        }

        function limparCamposEndereco() {
            const logradouro = document.getElementById("logradouro");
            const endereco = document.getElementById("endereco");
            const bairro = document.getElementById("bairro");
            const cidade = document.getElementById("cidade");

            if (logradouro) logradouro.value = "";
            if (endereco) endereco.value = "";
            if (bairro) bairro.value = "";
            if (cidade) cidade.value = "";
        }

        function montarEnderecoCompleto() {
            const logradouro = document.getElementById("logradouro") ? document.getElementById("logradouro").value.trim() : "";
            const numero = document.getElementById("numero") ? document.getElementById("numero").value.trim() : "";
            const bairro = document.getElementById("bairro") ? document.getElementById("bairro").value.trim() : "";
            const cidade = document.getElementById("cidade") ? document.getElementById("cidade").value.trim() : "";
            const cep = inputCep ? inputCep.value.trim() : "";

            if (!logradouro) return "";

            let enderecoCompleto = logradouro;
            if (numero) enderecoCompleto += `, ${numero}`;
            if (bairro) enderecoCompleto += ` - ${bairro}`;
            if (cidade) enderecoCompleto += `, ${cidade}`;
            if (cep) enderecoCompleto += `, CEP ${cep}`;

            return enderecoCompleto;
        }

        function atualizarEnderecoCompleto() {
            const campoEndereco = document.getElementById("endereco");
            const completo = montarEnderecoCompleto();
            if (campoEndereco) campoEndereco.value = completo;
        }
    });

    // --- FUNÇÕES DE INTERFACE (VISIBILIDADE) ---

    function toggleSenha() {
        const input = document.getElementById("senha");
        if (input) input.type = input.type === "password" ? "text" : "password";
    }

    function toggleConfirmarSenha() {
        const input = document.getElementById("confirmarSenha");
        if (input) input.type = input.type === "password" ? "text" : "password";
    }

    // --- admin validação do crud usuario ---

    function validarCampoEdit(campoId) {
        const input = document.getElementById(campoId);
        const erro = document.getElementById("erro-" + campoId);
        
        if (!input || !erro) return true;

        let valor = input.value.trim();
        
        // Remove caracteres especiais para contagem real
        let valorLimpo = valor;
        if (campoId === 'edit_cpf') valorLimpo = valor.replace(/\D/g, "");
        if (campoId === 'edit_telefone') valorLimpo = valor.replace(/\D/g, "");

        erro.textContent = "";
        input.style.borderColor = "";

        if (valor === "") {
            const labels = {
                'edit_nome': 'Nome',
                'edit_email': 'E-mail',
                'edit_telefone': 'Telefone',
                'edit_cpf': 'CPF'
            };
            erro.textContent = `${labels[campoId]} é obrigatório.`;
            input.style.borderColor = "red";
            return false;
        }

        // Validações específicas
        if (campoId === 'edit_nome' && valorLimpo.length < 3) {
            erro.textContent = "Nome deve ter pelo menos 3 caracteres.";
            input.style.borderColor = "red";
            return false;
        }

        if (campoId === 'edit_email') {
            const regexEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!regexEmail.test(valor)) {
                erro.textContent = "E-mail inválido.";
                input.style.borderColor = "red";
                return false;
            }
        }

        if (campoId === 'edit_cpf' && valorLimpo.length !== 11) {
            erro.textContent = "CPF deve ter 11 dígitos.";
            input.style.borderColor = "red";
            return false;
        }

        if (campoId === 'edit_telefone' && valorLimpo.length !== 11) {
            erro.textContent = "Telefone deve ter 11 dígitos.";
            input.style.borderColor = "red";
            return false;
        }

        return true;
    }

    // Adiciona validação ao submit do formulário de edição
    document.addEventListener("DOMContentLoaded", () => {
        const formEditar = document.getElementById("formEditarUsuario");
        if (formEditar) {
            formEditar.addEventListener("submit", (event) => {
                let formValido = true;
                
                ['edit_nome', 'edit_email', 'edit_cpf', 'edit_telefone'].forEach(campoId => {
                    if (!validarCampoEdit(campoId)) {
                        formValido = false;
                    }
                });

                if (!formValido) {
                    event.preventDefault();
                }
            });
        }
    });

    // --- LÓGICA DE AUTO-LOGOUT (TIMEOUT) - VERSÃO SEM COOKIE ---
let timeout;

function resetarTimer() {
    if (timeout) clearTimeout(timeout);
    
    const tempoLimite = 10000; // 10 segundos para teste

    timeout = setTimeout(() => {
        const path = window.location.pathname.toLowerCase();
        
        // Se a URL contiver 'login' ou 'cadastro', NÃO fazemos nada.
        const ehPaginaDeAcesso = path.includes('login') || path.includes('cadastro') || path === '/admin' || path === '/admin/';

        console.log("Verificando inatividade na página:", path);

        if (!ehPaginaDeAcesso) {
            console.warn("Inatividade detectada. Redirecionando forçadamente...");
            window.location.href = "/login?sessao_expirada=1";
        }
    }, tempoLimite);
}

// INICIALIZAÇÃO EM TODAS AS PÁGINAS
const eventosAtividade = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];

eventosAtividade.forEach(evento => {
    document.addEventListener(evento, resetarTimer, true);
});

// Inicia o cronómetro assim que a página carrega
resetarTimer();
console.log("Monitoramento de inatividade carregado e ativo.");