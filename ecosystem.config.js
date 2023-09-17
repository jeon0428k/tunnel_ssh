module.exports = {
    apps: [
        {
            name: "tunnel",
            script: "tunnel.js",
            watch: false,
            env: {
                NODE_ENV: "development",
            },
            env_production: {
                NODE_ENV: "production",
            },
        },
    ],
};