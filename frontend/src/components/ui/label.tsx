import * as React from 'react';
import { cn } from '../../lib/utils';

export interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {}

export const Label = React.forwardRef<HTMLLabelElement, LabelProps>(
  ({ className, ...props }, ref) => (
    <label
      ref={ref}
      className={cn('text-xs font-semibold leading-none text-slate-300 peer-disabled:cursor-not-allowed peer-disabled:opacity-70 select-none', className)}
      {...props}
    />
  )
);
Label.displayName = 'Label';
