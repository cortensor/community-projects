import React from "react";

/**
 * SpecialistSkeleton Component - Versão Final Refinada
 *
 * Este componente foi ajustado para máxima fidelidade visual com o componente real,
 * resolvendo as questões de cor e tamanho para uma experiência de usuário impecável.
 *
 * 1.  **Cor Mais Escura e Sutil:**
 *     - A cor de fundo dos elementos pulsantes foi alterada para `bg-[#2C2C30]`.
 *     - Este ajuste resulta em uma animação `animate-pulse` de baixíssimo contraste,
 *       criando um efeito visual muito mais sutil, profissional e integrado
 *       ao tema escuro da aplicação.
 *
 * 2.  **Altura Inicial Correta (Prevenção de Layout Shift):**
 *     - O placeholder do input expansível foi redimensionado de `h-20` para `h-10`.
 *     - Isso garante que a altura do skeleton corresponda exatamente à altura do
 *       componente `Specialist` em seu estado inicial (não expandido), eliminando
 *       qualquer "salto" de layout quando os dados são carregados.
 *
 * 3.  **Fidelidade Estrutural:** A estrutura geral continua espelhando o componente real,
 *     com placeholders para o nome, ícones, label e o rodapé fixo, garantindo
 *     consistência visual total.
 */
function SpecialistSkeleton() {
  return (
    <div className="w-full border border-[#3A3A3A] rounded-xl font-inter text-sm flex flex-col justify-between">
      {/* Seção Superior (Conteúdo) */}
      <div className="flex flex-col gap-3 p-4">
        {/* Cabeçalho: Nome e Ícones */}
        <div className="flex justify-between items-center">
          {/* Placeholder do Nome */}
          <div className="h-5 bg-[#2C2C30] rounded-md w-2/5 animate-pulse"></div>
          {/* Placeholders dos Ícones */}
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 bg-[#2C2C30] rounded-full animate-pulse"></div>
            <div className="h-8 w-8 bg-[#2C2C30] rounded-full animate-pulse"></div>
            <div className="h-8 w-8 bg-[#2C2C30] rounded-full animate-pulse"></div>
          </div>
        </div>

        {/* Seção do Prompt */}
        <div className="flex flex-col gap-2 mt-2">
          {/* Placeholder da Label */}
          <div className="h-3 bg-[#2C2C30] rounded-md w-1/4 animate-pulse"></div>

          {/* CORREÇÃO DE TAMANHO: Reduzido para h-10 para corresponder ao estado inicial do input */}
          <div className="h-10 bg-[#2C2C30] rounded-lg w-full animate-pulse"></div>
        </div>
      </div>

      {/* Seção Inferior (Botão Response) - Fixo, sem animação */}
      <div className="w-full h-10 bg-[#202024] rounded-b-[10px]"></div>
    </div>
  );
}

export default SpecialistSkeleton;