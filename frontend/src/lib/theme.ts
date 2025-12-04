// CBC-themed design system with Tailwind utility functions

// Color palette
export const colors = {
	primary: '#CC0000',      // CBC red
	primaryHover: '#A30000', // Darker CBC red for hover
	secondary: '#333333',    // Dark gray
	light: '#F7F7F7',       // Light background
	white: '#FFFFFF',
	success: '#10B981',      // Green
	successHover: '#059669',
	error: '#EF4444',        // Red
	errorHover: '#DC2626',
	warning: '#F59E0B',      // Amber
	info: '#3B82F6',         // Blue
	gray: {
		50: '#F9FAFB',
		100: '#F3F4F6',
		200: '#E5E7EB',
		300: '#D1D5DB',
		400: '#9CA3AF',
		500: '#6B7280',
		600: '#4B5563',
		700: '#374151',
		800: '#1F2937',
		900: '#111827'
	}
};

// Spacing scale
export const spacing = {
	xs: '4px',
	sm: '8px',
	md: '16px',
	lg: '24px',
	xl: '32px',
	'2xl': '48px',
	'3xl': '64px'
};

// Border radius
export const borderRadius = {
	sm: '4px',
	md: '8px',
	lg: '12px',
	xl: '16px',
	full: '9999px'
};

// Font sizes
export const fontSize = {
	xs: '0.75rem',      // 12px
	sm: '0.875rem',     // 14px
	base: '1rem',       // 16px
	lg: '1.125rem',     // 18px
	xl: '1.25rem',      // 20px
	'2xl': '1.5rem',    // 24px
	'3xl': '1.875rem',  // 30px
	'4xl': '2.25rem'    // 36px
};

// Shadows
export const shadows = {
	sm: '0 1px 2px 0 rgba(0,0,0,0.05)',
	md: '0 4px 6px -1px rgba(0,0,0,0.1)',
	lg: '0 10px 15px -3px rgba(0,0,0,0.1)',
	xl: '0 20px 25px -5px rgba(0,0,0,0.1)'
};

// Button variant utility
export function buttonVariants(
	variant: 'primary' | 'secondary' | 'success' | 'danger' | 'ghost' = 'primary',
	size: 'sm' | 'md' | 'lg' = 'md',
	disabled = false
): string {
	const baseClasses = 'font-semibold rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2';
	
	const sizeClasses = {
		sm: 'px-3 py-1.5 text-sm',
		md: 'px-4 py-2 text-base',
		lg: 'px-6 py-3 text-lg'
	};
	
	const variantClasses = {
		primary: disabled 
			? 'bg-gray-400 text-white cursor-not-allowed'
			: 'bg-[#CC0000] hover:bg-[#A30000] text-white focus:ring-[#CC0000]',
		secondary: disabled
			? 'bg-gray-300 text-gray-500 cursor-not-allowed'
			: 'bg-gray-200 hover:bg-gray-300 text-gray-800 focus:ring-gray-400',
		success: disabled
			? 'bg-gray-400 text-white cursor-not-allowed'
			: 'bg-green-600 hover:bg-green-700 text-white focus:ring-green-500',
		danger: disabled
			? 'bg-gray-400 text-white cursor-not-allowed'
			: 'bg-red-600 hover:bg-red-700 text-white focus:ring-red-500',
		ghost: disabled
			? 'text-gray-400 cursor-not-allowed'
			: 'text-gray-700 hover:bg-gray-100 focus:ring-gray-400'
	};
	
	return `${baseClasses} ${sizeClasses[size]} ${variantClasses[variant]}`;
}

// Input utility with error state
export function inputClasses(error?: string): string {
	const baseClasses = 'w-full rounded-lg transition-colors focus:outline-none focus:ring-2';
	const errorClasses = error
		? 'border-2 border-red-500 focus:ring-red-500 focus:border-red-500'
		: 'border border-gray-300 focus:ring-[#CC0000] focus:border-[#CC0000]';
	
	return `${baseClasses} ${errorClasses}`;
}

// Card utility
export function cardClasses(hover = false): string {
	const baseClasses = 'bg-white rounded-lg shadow-md border border-gray-200';
	const hoverClasses = hover ? 'hover:shadow-lg transition-shadow' : '';
	
	return `${baseClasses} ${hoverClasses}`;
}

// Alert variant utility
export function alertVariants(variant: 'error' | 'success' | 'warning' | 'info' = 'info'): string {
	const baseClasses = 'p-4 rounded-lg';
	
	const variantClasses = {
		error: 'bg-red-100 text-red-800 border border-red-200',
		success: 'bg-green-100 text-green-800 border border-green-200',
		warning: 'bg-amber-100 text-amber-800 border border-amber-200',
		info: 'bg-blue-100 text-blue-800 border border-blue-200'
	};
	
	return `${baseClasses} ${variantClasses[variant]}`;
}

// Badge variant utility
export function badgeVariants(variant: 'manual' | 'article' | 'synthetic' | 'default' = 'default'): string {
	const baseClasses = 'inline-block px-2 py-1 text-xs font-semibold rounded';
	
	const variantClasses = {
		manual: 'bg-blue-100 text-blue-800',
		article: 'bg-purple-100 text-purple-800',
		synthetic: 'bg-green-100 text-green-800',
		default: 'bg-gray-100 text-gray-800'
	};
	
	return `${baseClasses} ${variantClasses[variant]}`;
}
