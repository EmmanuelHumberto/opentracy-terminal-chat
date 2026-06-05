#!/bin/bash
# ============================================================================
# Instalacao do Docker e Docker Compose para LigadoAI
# ============================================================================

set -euo pipefail

echo "=========================================="
echo "  Instalacao do Docker - LigadoAI"
echo "=========================================="
echo ""

# Detecta a distribuicao
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
else
    echo "❌ Nao foi possivel detectar o sistema operacional."
    exit 1
fi

echo "Sistema: $OS $VER"
echo ""

instalar_docker_ubuntu_debian() {
    echo "📦 Atualizando pacotes..."
    sudo apt update -qq

    echo "📦 Instalando dependencias..."
    sudo apt install -y -qq \
        ca-certificates \
        curl \
        gnupg \
        lsb-release

    echo "🔑 Adicionando chave GPG do Docker..."
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/$OS/gpg | \
        sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    echo "📦 Adicionando repositorio Docker..."
    echo \
        "deb [arch=$(dpkg --print-architecture) \
        signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/$OS \
        $(lsb_release -cs) stable" | \
        sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    echo "📦 Instalando Docker..."
    sudo apt update -qq
    sudo apt install -y -qq \
        docker-ce \
        docker-ce-cli \
        containerd.io \
        docker-compose-plugin

    echo "👤 Adicionando usuario ao grupo docker..."
    sudo usermod -aG docker $USER
}

instalar_docker_fedora() {
    echo "📦 Instalando Docker no Fedora..."
    sudo dnf -y install dnf-plugins-core
    sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
    sudo dnf -y install docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo systemctl enable --now docker
    sudo usermod -aG docker $USER
}

instalar_docker_arch() {
    echo "📦 Instalando Docker no Arch Linux..."
    sudo pacman -S --noconfirm docker docker-compose
    sudo systemctl enable --now docker
    sudo usermod -aG docker $USER
}

# Executa instalacao conforme o SO
case "$OS" in
    ubuntu|debian|pop|linuxmint|elementary|zorin)
        instalar_docker_ubuntu_debian
        ;;
    fedora)
        instalar_docker_fedora
        ;;
    arch|manjaro|endeavouros)
        instalar_docker_arch
        ;;
    *)
        echo "⚠️  Sistema nao reconhecido: $OS"
        echo "   Instale o Docker manualmente: https://docs.docker.com/engine/install/"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "  ✅ Docker instalado com sucesso!"
echo "=========================================="
echo ""
echo "ℹ️  Para usar o Docker sem sudo, FAÇA LOGOUT e LOGIN novamente"
echo "   (ou execute: newgrp docker)"
echo ""
echo "📋 Verificar instalacao:"
echo "   docker --version"
echo "   docker compose version"
echo ""
echo "🚀 Proximo passo:"
echo "   bash scripts/setup_banco.sh"
echo ""
