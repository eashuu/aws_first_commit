import './Button.css';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary';
  children: React.ReactNode;
}

/**
 * Button — Typed glassmorphic button component.
 * Variant drives the class modifier; all interaction states live in CSS.
 */
export function Button({ variant = 'secondary', className = '', children, ...props }: ButtonProps) {
  return (
    <button
      className={`btn btn-${variant} ${className}`.trim()}
      {...props}
    >
      {children}
    </button>
  );
}
