import * as React from 'react';
import { cn } from '../../lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  size?: 'default' | 'sm' | 'lg' | 'icon';
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => {
    const variants = {
      default: 'bg-emerald-600 text-white shadow-xs hover:bg-emerald-500 active:scale-[0.98] font-bold',
      destructive: 'bg-red-950/40 text-red-400 border border-red-500/30 hover:bg-red-900/60 active:scale-[0.98]',
      outline: 'border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-slate-200 hover:text-white active:scale-[0.98]',
      secondary: 'bg-slate-800 text-slate-200 hover:bg-slate-700 border border-slate-700/80 active:scale-[0.98]',
      ghost: 'hover:bg-slate-800 hover:text-slate-100 text-slate-400 active:scale-[0.98]',
      link: 'text-emerald-400 underline-offset-4 hover:underline',
    };

    const sizes = {
      default: 'h-9 px-4 py-2 text-sm',
      sm: 'h-8 rounded-md px-3 text-xs',
      lg: 'h-10 rounded-md px-6 text-sm',
      icon: 'h-9 w-9 p-0',
    };

    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg font-medium transition-all focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-zinc-400 disabled:pointer-events-none disabled:opacity-50 cursor-pointer select-none',
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';
