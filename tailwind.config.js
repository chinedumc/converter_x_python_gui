/** @type {import('tailwindcss').Config} */
module.exports = {
	content: [
		"./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
		"./src/components/**/*.{js,ts,jsx,tsx,mdx}",
		"./src/app/**/*.{js,ts,jsx,tsx,mdx}",
	],
	theme: {
		extend: {
			colors: {
				wine: {
					50: "#fcf5f5",
					100: "#f9ebeb",
					200: "#f0cccc",
					300: "#e7adad",
					400: "#d67070",
					500: "#c43232",
					600: "#b02d2d",
					700: "#932626",
					800: "#761e1e",
					900: "#601919",
				},
			},
			animation: {
				progress: "progress 1s ease-in-out infinite",
			},
			keyframes: {
				progress: {
					"0%": { width: "0%" },
					"100%": { width: "100%" },
				},
			},
		},
	},
	plugins: [],
};
