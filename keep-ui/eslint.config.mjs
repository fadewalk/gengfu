export default [
  { ignores: ["**/node_modules", "**/.next", "**/dist", "**/build"] },
  {
    files: ["**/*.{ts,tsx}"],
    rules: {
      "no-unused-vars": "off",
    },
  },
];
