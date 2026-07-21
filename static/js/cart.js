// --- LÓGICA GLOBAL DA SACOLA DE COMPRAS ---

// 1. Adicionar item ao carrinho
function addToCart(nome, preco, tamanho, cor) {
    let cart = JSON.parse(localStorage.getItem('cart')) || [];

    // Procura se o item com a MESMA cor e TAMANHO já existe
    const index = cart.findIndex(item => item.nome === nome && item.tamanho === tamanho && item.cor === cor);

    if (index > -1) {
        cart[index].qtd += 1;
    } else {
        cart.push({
            nome: nome,
            preco: parseFloat(preco),
            tamanho: tamanho || 'Padrão',
            cor: cor || 'Padrão',
            qtd: 1
        });
    }

    localStorage.setItem('cart', JSON.stringify(cart));
    atualizarBarraSacola();
}

// 2. Atualiza a barra flutuante na loja e o contador no header
function atualizarBarraSacola() {
    const cart = JSON.parse(localStorage.getItem('cart')) || [];
    const totalItens = cart.reduce((sum, item) => sum + item.qtd, 0);

    const floatingBar = document.getElementById('cart-floating-bar');
    const cartCounter = document.getElementById('cart-counter');

    if (cartCounter) {
        cartCounter.innerText = totalItens;
    }

    if (floatingBar) {
        if (totalItens > 0) {
            floatingBar.style.display = 'flex';
        } else {
            floatingBar.style.display = 'none';
        }
    }
}

// Executa ao carregar a página para atualizar o contador da barra
document.addEventListener("DOMContentLoaded", atualizarBarraSacola);