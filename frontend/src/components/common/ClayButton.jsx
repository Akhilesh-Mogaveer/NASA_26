import React from 'react';

/**
 * ClayButton — Tactile Claymorphic Interactive Button
 * 
 * Provides tactile outer drop shadow, specular inner highlight, and active inset press state.
 */
export default function ClayButton({
  variant = 'secondary',
  size = 'md',
  icon: Icon,
  children,
  disabled = false,
  onClick,
  className = '',
  type = 'button',
  ...props
}) {
  const sizeStyles = {
    sm: 'px-2.5 py-1 text-xs rounded-lg gap-1.5',
    md: 'px-3.5 py-1.5 text-xs font-semibold rounded-xl gap-2',
    lg: 'px-4 py-2 text-sm font-semibold rounded-xl gap-2.5',
  };

  const variantStyles = {
    primary:
      'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white border border-white/20 shadow-clay',
    secondary:
      'bg-space-800/90 hover:bg-space-700/90 text-space-200 hover:text-white border border-white/10 shadow-clay-sm',
    accent:
      'bg-gradient-to-r from-sky-500 to-cyan-500 hover:from-sky-400 hover:to-cyan-400 text-white border border-white/20 shadow-clay',
    modis:
      'bg-gradient-to-r from-modis to-amber-600 hover:from-modis-dark hover:to-amber-500 text-white border border-white/20 shadow-clay',
    viirs:
      'bg-gradient-to-r from-viirs to-rose-600 hover:from-viirs-dark hover:to-rose-500 text-white border border-white/20 shadow-clay',
    danger:
      'bg-rose-600 hover:bg-rose-500 text-white border border-rose-400/30 shadow-clay-sm',
    ghost:
      'bg-transparent hover:bg-white/[0.06] text-space-300 hover:text-white border border-transparent',
  };

  const selectedSize = sizeStyles[size] || sizeStyles.md;
  const selectedVariant = variantStyles[variant] || variantStyles.secondary;

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`clay-button inline-flex items-center justify-center font-medium transition-all duration-180 disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none select-none ${selectedSize} ${selectedVariant} ${className}`}
      {...props}
    >
      {Icon && <Icon className="w-3.5 h-3.5 flex-shrink-0" />}
      {children}
    </button>
  );
}
