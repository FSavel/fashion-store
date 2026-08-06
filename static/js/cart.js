// ==========================================
// --- LÓGICA GLOBAL DA SACOLA DE COMPRAS ---
// ==========================================

/**
 * Obtém os itens do carrinho com validação de erros.
 * @returns {Array} Lista de itens do carrinho
 */
function getCart() {
    try {
        const cartData = localStorage.getItem('cart');
        return cartData ? JSON.parse(cartData) : [];
    } catch (e) {
        console.error("Erro ao ler o carrinho do localStorage:", e);
        return [];
    }
}

/**
 * Guarda a lista atualizada no localStorage.
 * @param {Array} cart - Lista de itens
 */
function saveCart(cart) {
    try {
        localStorage.setItem('cart', JSON.stringify(cart));
    } catch (e) {
        console.error("Erro ao guardar o carrinho no localStorage:", e);
    }
}

/**
 * Adiciona um item ao carrinho ou incrementa a quantidade se já existir.
 * @param {string} nome 
 * @param {number|string} preco 
 * @param {string} tamanho 
 * @param {string} cor 
 * @param {string|number} [id=null] 
 * @param {string} [foto=''] 
 */
function addToCart(nome, preco, tamanho, cor, id = null, foto = '') {
    let cart = getCart();

    const tamanhoValido = (tamanho && tamanho.trim() !== '') ? tamanho.trim() : 'Padrão';
    const corValida = (cor && cor.trim() !== '') ? cor.trim() : 'Padrão';
    const precoNum = parseFloat(preco) || 0;

    // Procura se o item com a mesma variação (Nome + Tamanho + Cor) já existe
    const index = cart.findIndex(item => 
        item.nome === nome && 
        item.tamanho === tamanhoValido && 
        item.cor === corValida
    );

    if (index > -1) {
        cart[index].qtd += 1;
    } else {
        cart.push({
            id: id,
            nome: nome,
            preco: precoNum,
            tamanho: tamanhoValido,
            cor: corValida,
            foto: foto,
            qtd: 1
        });
    }

    saveCart(cart);
    atualizarBarraSacola();
    exibirNotificacaoToast(`"${nome}" adicionado à sacola!`);
}

/**
 * Altera a quantidade de um item específico pelo índice no carrinho.
 * @param {number} index 
 * @param {number} delta (+1 para somar, -1 para subtrair)
 */
function alterarQuantidade(index, delta) {
    let cart = getCart();
    if (cart[index]) {
        cart[index].qtd += delta;
        if (cart[index].qtd <= 0) {
            cart.splice(index, 1);
        }
        saveCart(cart);
        atualizarBarraSacola();
        
        // Dispara evento customizado para páginas que renderizam a lista do carrinho
        document.dispatchEvent(new CustomEvent('cartUpdated', { detail: { cart } }));
    }
}

/**
 * Remove completamente um item do carrinho pelo índice.
 * @param {number} index 
 */
function removerDoCarrinho(index) {
    let cart = getCart();
    if (cart[index]) {
        cart.splice(index, 1);
        saveCart(cart);
        atualizarBarraSacola();

        document.dispatchEvent(new CustomEvent('cartUpdated', { detail: { cart } }));
    }
}

/**
 * Esvazia todo o carrinho de compras.
 */
function limparCarrinho() {
    localStorage.removeItem('cart');
    atualizarBarraSacola();
    document.dispatchEvent(new CustomEvent('cartUpdated', { detail: { cart: [] } }));
}

/**
 * Calcula o valor total financeiro acumulado no carrinho.
 * @returns {number} Valor total em MT
 */
function calcularTotalCarrinho() {
    const cart = getCart();
    return cart.reduce((total, item) => total + (item.preco * item.qtd), 0);
}

/**
 * Atualiza os contadores e a visibilidade da barra flutuante.
 */
function atualizarBarraSacola() {
    const cart = getCart();
    const totalItens = cart.reduce((sum, item) => sum + item.qtd, 0);

    const floatingBar = document.getElementById('cart-floating-bar');
    const cartCounter = document.getElementById('cart-counter');

    if (cartCounter) {
        cartCounter.innerText = totalItens;
    }

    if (floatingBar) {
        floatingBar.style.display = totalItens > 0 ? 'flex' : 'none';
    }
}

/**
 * Exibe uma pequena notificação temporária no topo da tela.
 * @param {string} mensagem 
 */
function exibirNotificacaoToast(mensagem) {
    let toast = document.getElementById('cart-toast-notification');
    
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'cart-toast-notification';
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%) translateY(-100px);
            background: #0f172a;
            color: #ffffff;
            padding: 12px 24px;
            border-radius: 25px;
            font-size: 13px;
            font-weight: 700;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            z-index: 2000;
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            pointer-events: none;
        `;
        document.body.appendChild(toast);
    }

    toast.innerText = mensagem;
    toast.style.transform = 'translateX(-50%) translateY(0)';

    clearTimeout(window.toastTimer);
    window.toastTimer = setTimeout(() => {
        toast.style.transform = 'translateX(-50%) translateY(-100px)';
    }, 2500);
}

// Executa ao carregar o documento
document.addEventListener("DOMContentLoaded", atualizarBarraSacola);
