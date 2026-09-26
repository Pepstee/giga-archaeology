import { buildService, RenamedService } from "@app/barrel";

const service: RenamedService = buildService();
service.greet("world");
