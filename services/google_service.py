// Estado do Carrinho em memória / localStorage
let carrinho = JSON.parse(localStorage.getItem('carrinho_loja')) || [];
let produtoSelecionado = null;

// Salvar no LocalStorage
function salvarCarrinho() {
    localStorage.setItem('carrinho_loja', JSON.stringify(carrinho));
    atualizarBarraCarrinho();
}

// Atualiza o contador e valor total no botão flutuante
function atualizarBarraCarrinho() {
    const totalItens = carrinho.reduce((acc, item) => acc + item.quantidade, 0);
    const totalValor = carrinho.reduce((acc, item) => acc + (item.preco * item.quantidade), 0);

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
        const catProduto = card.getAttribute('data-categoria');
        if (categoria === 'todas' || catProduto.toLowerCase() === categoria.toLowerCase()) {
            card.style.display = 'flex';
        } else {
            card.style.display = 'none';
        }
    });
}

// Adicionar Produto com Tamanho e Cor
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
    alert(`${nome} (${tamanho}, ${cor}) adicionado ao carrinho!`);
}

// Enviar Pedido via WhatsApp
function finalizarPedidoWhatsApp(numeroWhatsapp, nomeCliente) {
    if (carrinho.length === 0) {
        alert("O seu carrinho está vazio!");
        return;
    }

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

    // Enviar cópia para o backend Flask (Google Sheets) em segundo plano
    fetch('/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            nome: nomeCliente,
            contacto: "Via WhatsApp",
            cart: carrinho
        })
    }).catch(err => console.log("Erro ao sincronizar com servidor, enviado apenas via WhatsApp"));

    // Redireciona para o WhatsApp do vendedor
    const url = `https://wa.me/${numeroWhatsapp}?text=${encodeURIComponent(texto)}`;
    window.open(url, '_blank');

    // Limpa carrinho após finalizar
    carrinho = [];
    salvarCarrinho();
}

// Inicializar na carga da página
document.addEventListener('DOMContentLoaded', () => {
    atualizarBarraCarrinho();
});