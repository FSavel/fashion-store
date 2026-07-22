// ==========================================
// ESTADO DO CARRINHO (LocalStorage)
// ==========================================
let carrinho = JSON.parse(localStorage.getItem('carrinho_loja')) || [];
let produtoTemp = null;

/**
 * Limpa e converte qualquer preço/texto para um número válido (float).
 * Resolve problemas de espaços de milhares (ex: "2 500"), vírgulas e "MT".
 */
function limparPreco(valor) {
    if (typeof valor === 'number') return valor;
    if (!valor) return 0;
    
    // 1. Converte para string e remove todos os tipos de espaços (normais e invisíveis/NBSP)
    let texto = valor.toString().replace(/\s+/g, '').replace(/\u00A0/g, '');

    // 2. Trata vírgulas e pontos:
    if (texto.includes(',') && texto.includes('.')) {
        if (texto.indexOf('.') < texto.indexOf(',')) {
            // Formato europeu/PT (2.500,00) -> remove ponto e troca vírgula por ponto
            texto = texto.replace(/\./g, '').replace(',', '.');
        } else {
            // Formato americano (2,500.00) -> remove vírgula
            texto = texto.replace(/,/g, '');
        }
    } else if (texto.includes(',')) {
        // Se só tiver vírgula (ex: 2500,00), troca por ponto
        texto = texto.replace(',', '.');
    }

    // 3. Remove tudo o que não for número ou ponto decimal
    let textoLimpo = texto.replace(/[^0-9.]/g, '');
    let numero = parseFloat(textoLimpo);
    
    return isNaN(numero) ? 0 : numero;
}

// Guardar estado no LocalStorage e atualizar a interface
function salvarCarrinho() {
    localStorage.setItem('carrinho_loja', JSON.stringify(carrinho));
    atualizarBarraCarrinho();
    if (typeof renderizarCarrinho === 'function') {
        renderizarCarrinho();
    }
}

// Atualiza o contador de itens e valor total no botão flutuante
function atualizarBarraCarrinho() {
    const totalItens = carrinho.reduce((acc, item) => acc + (parseInt(item.quantidade) || 1), 0);
    const totalValor = carrinho.reduce((acc, item) => {
        const precoNum = limparPreco(item.preco);
        const qtdNum = parseInt(item.quantidade) || 1;
        return acc + (precoNum * qtdNum);
    }, 0);

    const countEl = document.getElementById('cart-count');
    const totalEl = document.getElementById('cart-total');

    if (countEl) countEl.innerText = totalItens;
    if (totalEl) totalEl.innerText = `${totalValor.toFixed(2)} MT`;
}

// Renderiza a lista do carrinho no ecrã (caso exista um container específico)
function renderizarCarrinho() {
    const container = document.getElementById('cart-items-container') || document.getElementById('itens-carrinho');
    if (!container) return;

    if (carrinho.length === 0) {
        container.innerHTML = `<p style="text-align:center; padding: 20px;">A sua sacola está vazia.</p>`;
        return;
    }

    let html = '';
    carrinho.forEach((item, idx) => {
        const precoNum = limparPreco(item.preco);
        const subtotal = precoNum * item.quantidade;
        html += `
            <div class="cart-item" style="display:flex; justify-between; align-items:center; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 10px;">
                <div>
                    <strong>${item.nome}</strong><br>
                    <small>Tam: ${item.tamanho} | Cor: ${item.cor}</small><br>
                    <small>${item.quantidade}x ${precoNum.toFixed(2)} MT = <strong>${subtotal.toFixed(2)} MT</strong></small>
                </div>
                <button onclick="removerDoCarrinho(${idx})" style="background:#ff4d4d; color:#fff; border:none; padding:5px 10px; border-radius:4px; cursor:pointer;">X</button>
            </div>
        `;
    });
    container.innerHTML = html;
}

// Remover um item do carrinho pelo índice
function removerDoCarrinho(index) {
    carrinho.splice(index, 1);
    salvarCarrinho();
}

// Filtrar por categoria na página principal
function filtrar(categoria) {
    const cards = document.querySelectorAll('.product-card');
    const botoes = document.querySelectorAll('.btn-cat');

    botoes.forEach(btn => {
        if (btn.innerText.toLowerCase() === categoria.toLowerCase() || (categoria === 'todas' && btn.innerText === 'Todas')) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    cards.forEach(card => {
        const catProduto = card.getAttribute('data-categoria') || '';
        if (categoria === 'todas' || catProduto.toLowerCase() === categoria.toLowerCase()) {
            card.style.display = 'flex';
        } else {
            card.style.display = 'none';
        }
    });
}

// Abrir Modal de Escolha de Tamanho / Cor
function abrirModalVariacoes(id, nome, preco, tamanhosStr, coresStr) {
    const tamanhos = tamanhosStr ? tamanhosStr.split(',').map(s => s.trim()) : ['Único'];
    const cores = coresStr ? coresStr.split(',').map(s => s.trim()) : ['Padrão'];

    let tamanhoSel = tamanhos[0];
    let corSel = cores[0];

    // Adiciona diretamente ao carrinho
    adicionarAoCarrinho(id, nome, preco, tamanhoSel, corSel);
}

// Adicionar Produto ao Carrinho
function adicionarAoCarrinho(id, nome, preco, tamanho, cor) {
    const precoNumerico = limparPreco(preco);
    const itemExistente = carrinho.find(item => item.id === id && item.tamanho === tamanho && item.cor === cor);

    if (itemExistente) {
        itemExistente.quantidade += 1;
    } else {
        carrinho.push({
            id: id,
            nome: nome,
            preco: precoNumerico,
            tamanho: tamanho,
            cor: cor,
            quantidade: 1
        });
    }

    salvarCarrinho();
    alert(`"${nome}" (${tamanho} / ${cor}) foi adicionado ao carrinho!`);
}

// Abrir resumo do carrinho e perguntar forma de envio
function abrirCarrinho() {
    if (!carrinho || carrinho.length === 0) {
        alert("O seu carrinho está vazio. Adicione algumas peças primeiro!");
        return;
    }

    const nomeCliente = prompt("Digite o seu Nome para confirmar o pedido:", "Cliente");
    if (!nomeCliente) return;

    // Número configurado para WhatsApp e SMS
    const numeroLoja = document.body.getAttribute('data-whatsapp') || "258879131089";

    // Pergunta ao cliente qual canal prefere usar
    const opcao = prompt("Como deseja enviar o pedido?\n1 - WhatsApp\n2 - SMS", "1");

    if (opcao === "2") {
        finalizarPedidoSMS(numeroLoja, nomeCliente);
    } else {
        finalizarPedidoWhatsApp(numeroLoja, nomeCliente);
    }
}

// Finalizar e enviar Pedido via WhatsApp
function finalizarPedidoWhatsApp(numeroWhatsapp, nomeCliente) {
    if (!carrinho || carrinho.length === 0) {
        alert("O seu carrinho está vazio.");
        return;
    }

    let texto = `*NOVO PEDIDO - BOUTIQUE*\n`;
    texto += `*Cliente:* ${nomeCliente}\n`;
    texto += `------------------------------------\n`;

    let total = 0;
    carrinho.forEach(item => {
        const precoNum = limparPreco(item.preco);
        const subtotal = precoNum * item.quantidade;
        total += subtotal;
        texto += `• ${item.quantidade}x ${item.nome}\n  *Tam:* ${item.tamanho} | *Cor:* ${item.cor}\n  *Val:* ${subtotal.toFixed(2)} MT\n\n`;
    });

    texto += `------------------------------------\n`;
    texto += `*TOTAL:* ${total.toFixed(2)} MT`;

    // 1. Regista no backend (Google Sheets/Admin)
    fetch('/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            nome: nomeCliente,
            contacto: "Via WhatsApp",
            cart: carrinho
        })
    }).then(res => res.json())
      .then(data => console.log("Pedido registado no Admin:", data))
      .catch(err => console.log("Erro ao registar no backend, enviado via WhatsApp."));

    // 2. Redireciona para o WhatsApp
    const url = `https://wa.me/${numeroWhatsapp}?text=${encodeURIComponent(texto)}`;
    window.open(url, '_blank');

    // 3. Limpa o carrinho e atualiza o ecrã imediatamente
    carrinho = [];
    salvarCarrinho();
}

// Finalizar e enviar Pedido via SMS
function finalizarPedidoSMS(numeroSMS, nomeCliente) {
    if (!carrinho || carrinho.length === 0) {
        alert("O seu carrinho está vazio.");
        return;
    }

    let texto = `NOVO PEDIDO - BOUTIQUE\n`;
    texto += `Cliente: ${nomeCliente}\n`;
    texto += `------------------------------------\n`;

    let total = 0;
    carrinho.forEach(item => {
        const precoNum = limparPreco(item.preco);
        const subtotal = precoNum * item.quantidade;
        total += subtotal;
        texto += `• ${item.quantidade}x ${item.nome} (${item.tamanho}/${item.cor}): ${subtotal.toFixed(2)} MT\n`;
    });

    texto += `------------------------------------\n`;
    texto += `TOTAL: ${total.toFixed(2)} MT`;

    // 1. Regista no backend (Google Sheets/Admin)
    fetch('/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            nome: nomeCliente,
            contacto: "Via SMS",
            cart: carrinho
        })
    }).then(res => res.json())
      .then(data => console.log("Pedido registado no Admin:", data))
      .catch(err => console.log("Erro ao registar no backend, enviado via SMS."));

    // 2. Abre a aplicação de SMS no telemóvel
    const url = `sms:${numeroSMS}?body=${encodeURIComponent(texto)}`;
    window.location.href = url;

    // 3. Limpa o carrinho e atualiza o ecrã imediatamente
    carrinho = [];
    salvarCarrinho();
}

// Inicialização automática ao carregar o ecrã
document.addEventListener('DOMContentLoaded', () => {
    atualizarBarraCarrinho();
    if (typeof renderizarCarrinho === 'function') {
        renderizarCarrinho();
    }
});
