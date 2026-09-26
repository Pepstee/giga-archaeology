export interface Greeter {
  greet(name: string): string;
}

export class Service implements Greeter {
  greet(name: string): string {
    return `hello ${name}`;
  }
}

export function buildService(): Service {
  return new Service();
}
