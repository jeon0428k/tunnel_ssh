const {Client} = require('ssh2');

const RECONNECT_MS = 1000;
const READY_EVENT = "ready";
const CONFIG = {
    name: "identity-name",
    username: "ssh-username",
    password: "ssh-password",
    host: "127.0.0.1",
    port: 22,
    dstHost: "127.0.0.1",
    dstPort: null,
    localHost: "127.0.0.1",
    localPort: 0,
    keepaliveInterval: 30000,
};

class Tunnel {
    constructor(config) {
        this.config = config;
    }
    start = () => {
        const config = this.config;
        console.info(`[${config.name}] tunnel start`);
        const options = {
            username: config.username,
            password: config.password,
            host: config.host,
            port: config.port,
        }
        const jumpClient = new Client()
            .on(READY_EVENT, () => {
                this.jumpListener(jumpClient);
            })
            .on('error', (err) => {
                console.error(`[${config.name}] connection error for jump tunnel. (${err.level}) ${err}`);
                this.reconnect(jumpClient, options);
            })
            .connect(options);
    };
    reconnect = (client, options) => {
        setTimeout(() => {
            client.connect(options);
        }, RECONNECT_MS);
    };
    jumpListener = (jumpClient) => {
        const config = this.config;
        console.info(`[${config.name}] jump tunnel ready`);
        jumpClient.forwardOut(
            config.localHost,
            config.localPort,
            config.dstHost,
            config.dstPort,
            (err, stream) => {
                if (err) throw err;
                const options = {
                    sock: stream,
                    username: config.username,
                    password: config.password,
                    host: config.dstHost,
                    port: config.dstPort,
                }
                const targetClient = new Client()
                    .on(READY_EVENT, () => {
                        this.targetListener(targetClient);
                    })
                    .on('error', (err) => {
                        console.error(`[${config.name}] connection error for target tunnel. (${err.level}) ${err}`);
                        this.reconnect(targetClient, options);
                    })
                    .connect(options);
            });
    };
    targetListener = (client) => {
        const config = this.config;
        console.info(`[${config.name}] target tunnel ready`);
        setInterval(() => {
            client.exec("ls", () => {
            });
        }, config.keepaliveInterval);
        client.exec('ls /', function (err, stream) {
            if (err) throw err;
            stream.on('close', function (code, signal) {
                console.info(`[${config.name}] stream closed with code ${code} and signal ${signal}`);
                client.end();
            }).on('data', function (data) {
                console.info(`[${config.name}] stdout: ${data}`);
            }).stderr.on('data', function (data) {
                console.error(`[${config.name}] stderr: ${data}`);
            });
        });
    };
}

module.exports = {
    Tunnel
};