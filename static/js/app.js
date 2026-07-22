// Estado do Carrinho em memória / localStorage
let carrinho = JSON.parse(localStorage.getItem('carrinho_loja')) || [];
let produtoTemp = null;

// Salvar no LocalStorage
function salvarCarrinho() {
    localStorage.setItem('carrinho_loja', JSON.stringify(carrinho));
    atualizarBarraCarrinho();
}

// Atualiza o contador e valor total no botão flutuante
function atualizarBarraCarrinho() {
    const totalItens = carrinho.reduce((acc, item) => acc + item.quantidade, 0);
    const totalValor = carrinho.reduce((acc, item) => acc + (parseFloat(item.preco) * item.quantidade), 0);

    const countEl = document.getElementById('cart-count');
    const totalEl = document.getElementById('cart-total');

    if (countEl) countEl.innerText = totalItens;
    if (totalEl) totalEl.innerText = `${totalValor.toFixed(2)} MT`;
}

// Filtrar por categoria no ecrã principal
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

    // Adiciona diretamente ao carrinho com as opções padrão ou únicas
    adicionarAoCarrinho(id, nome, preco, tamanhoSel, corSel);
}

// Adicionar Produto ao Carrinho
function adicionarAoCarrinho(id, nome, preco, tamanho, cor) {
    const itemExistente = carrinho.find(item => item.id === id && item.tamanho === tamanho && item.cor === cor);

    if (itemExistente) {
        itemExistente.quantidade += 1;
    } else {
        carrinho.push({
            id: id,
            nome: nome,
            preco: parseFloat(preco),
            tamanho: tamanho,
            cor: cor,
            quantidade: 1
        });
    }

    salvarCarrinho();
    alert(`"${nome}" (${tamanho} / ${cor}) foi adicionado ao carrinho!`);
}

// Abrir Modal / Resumo do Carrinho ao Clicar na Barra Flutuante
function abrirCarrinho() {
    if (carrinho.length === 0) {
        alert("O seu carrinho está vazio. Adicione algumas peças primeiro!");
        return;
    }

    const nomeCliente = prompt("Digite o seu Nome para confirmar o pedido:", "Cliente");
    if (!nomeCliente) return;

    // Número fixado para WhatsApp e SMS: 258879131089
    const numeroLoja = document.body.getAttribute('data-whatsapp') || "258879131089";

    // Pergunta ao cliente como prefere enviar
    const opcao = prompt("Como deseja enviar o pedido?\n1 - WhatsApp\n2 - SMS", "1");

    if (opcao === "2") {
        finalizarPedidoSMS(numeroLoja, nomeCliente);
    } else {
        finalizarPedidoWhatsApp(numeroLoja, nomeCliente);
    }
}

// Enviar Pedido via WhatsApp
function finalizarPedidoWhatsApp(numeroWhatsapp, nomeCliente) {
    let texto = `*NOVO PEDIDO - BOUTIQUE*\n`;
    texto += `*Cliente:* ${nomeCliente}\n`;
    texto += `------------------------------------\n`;

    let total = 0;
    carrinho.forEach(item => {
        const subtotal = item.preco * item.quantidade;
        total += subtotal;
        texto += `• ${item.quantidade}x ${item.nome}\n  *Tam:* ${item.tamanho} | *Cor:* ${item.cor}\n  *Val:* ${subtotal.toFixed(2)} MT\n\n`;
    });

    texto += `------------------------------------\n`;
    texto += `*TOTAL:* ${total.toFixed(2)} MT`;

    // Regista no Google Sheets em background
    fetch('/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            nome: nomeCliente,
            contacto: "Via WhatsApp",
            cart: carrinho
        })
    }).catch(err => console.log("Sincronização em segundo plano offline. Enviado via WhatsApp."));

    // Redireciona para o WhatsApp
    const url = `https://wa.me/${numeroWhatsapp}?text=${encodeURIComponent(texto)}`;
    window.open(url, '_blank');

    // Limpa carrinho
    carrinho = [];
    salvarCarrinho();
}

// Enviar Pedido via SMS
function finalizarPedidoSMS(numeroSMS, nomeCliente) {
    let texto = `NOVO PEDIDO - BOUTIQUE\n`;
    texto += `Cliente: ${nomeCliente}\n`;
    texto += `------------------------------------\n`;

    let total = 0;
    carrinho.forEach(item => {
        const subtotal = item.preco * item.quantidade;
        total += subtotal;
        texto += `• ${item.quantidade}x ${item.nome} (${item.tamanho}/${item.cor}): ${subtotal.toFixed(2)} MT\n`;
    });

    texto += `------------------------------------\n`;
    texto += `TOTAL: ${total.toFixed(2)} MT`;

    // Regista no Google Sheets em background
    fetch('/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            nome: nomeCliente,
            contacto: "Via SMS",
            cart: carrinho
        })
    }).catch(err => console.log("Sincronização em segundo plano offline. Enviado via SMS."));

    // Abre a aplicação de SMS no telemóvel do cliente
    const url = `sms:${numeroSMS}?body=${encodeURIComponent(texto)}`;
    window.location.href = url;

    // Limpa carrinho
    carrinho = [];
    salvarCarrinho();
}

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    atualizarBarraCarrinho();
});
