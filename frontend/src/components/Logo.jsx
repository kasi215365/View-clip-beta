import React from 'react';

/**
 * View/Clip logo — the "/" is the central design element.
 * Props: size ('sm'|'md'|'lg'), animated (bool)
 */
export const Logo = ({ size = 'md', animated = false, className = '' }) => {
  const sizes = {
    sm: { text: 'text-xl', slash: 'text-2xl', gap: 'space-x-0.5' },
    md: { text: 'text-2xl', slash: 'text-3xl', gap: 'space-x-0.5' },
    lg: { text: 'text-4xl sm:text-5xl', slash: 'text-5xl sm:text-6xl', gap: 'space-x-1' },
  };
  const s = sizes[size] || sizes.md;

  return (
    <div data-testid="viewclip-logo" className={`flex items-baseline ${s.gap} font-bold tracking-tight ${className}`}>
      <span className={`${s.text} text-white`}>View</span>
      <span
        className={`${s.slash} bg-gradient-to-br from-cyan-300 via-cyan-400 to-fuchsia-500 bg-clip-text text-transparent ${animated ? 'animate-slash-spin' : ''}`}
        style={{ display: 'inline-block', fontStyle: 'italic', fontWeight: 900 }}
      >
        /
      </span>
      <span className={`${s.text} text-white`}>Clip</span>
    </div>
  );
};

export default Logo;
