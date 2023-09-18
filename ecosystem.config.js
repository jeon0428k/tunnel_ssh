const fs = require('fs');
const JSON5 = require('json5');

const CONFIG_FILES = [
    "config/config.json",
    "config/config_kr.json",
];
const apps = CONFIG_FILES.flatMap(filePath => {
    const configs = JSON5.parse(fs.readFileSync(filePath, 'utf8'));
    return configs.map(config => {
        return {
            name: "tunnel",
            script: "main.js",
            watch: true,
            daemon_mode: false,
            restart: false,
            env: {
                CONFIG: JSON.stringify(config),
            },
            exec_mode: "fork"
        }
    });
});
module.exports = {
    apps: apps,
};
