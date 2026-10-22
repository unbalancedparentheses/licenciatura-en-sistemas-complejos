{
  description = "Licenciatura en Sistemas Complejos — UBA program proposal site";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        # Pinned to the release CI uses (.github/workflows/deploy.yml).
        # Zola 0.23 moved to Tera 2, which these templates don't support yet.
        zolaVersion = "0.22.1";
        zolaRelease = {
          aarch64-darwin = { target = "aarch64-apple-darwin"; hash = "sha256-RqxFqedijbqFk7Ek7oeU9PmqHGtWmRjs1LvF0L4ZBRU="; };
          x86_64-darwin = { target = "x86_64-apple-darwin"; hash = "sha256-OJhwnhVK4Fk5MyZKVAyGk0i9sQ1/GwOkLft41jcDs7U="; };
          x86_64-linux = { target = "x86_64-unknown-linux-gnu"; hash = "sha256-DKCapAN2qqnd+1Ev+a2WMmLvle2w0PLV7GlhtvXPIu8="; };
          aarch64-linux = { target = "aarch64-unknown-linux-gnu"; hash = "sha256-ivQ37GNS8zzNJNehz8tUo9uV0843bcaVJbTvP7a4wdE="; };
        }.${system};
        zola = pkgs.stdenv.mkDerivation {
          pname = "zola";
          version = zolaVersion;
          src = pkgs.fetchurl {
            url = "https://github.com/getzola/zola/releases/download/v${zolaVersion}/zola-v${zolaVersion}-${zolaRelease.target}.tar.gz";
            inherit (zolaRelease) hash;
          };
          sourceRoot = ".";
          nativeBuildInputs = pkgs.lib.optionals pkgs.stdenv.isLinux [ pkgs.autoPatchelfHook ];
          buildInputs = pkgs.lib.optionals pkgs.stdenv.isLinux [ pkgs.stdenv.cc.cc.lib ];
          installPhase = "install -Dm755 zola $out/bin/zola";
        };
      in {
        devShells.default = pkgs.mkShell {
          packages = [ zola ] ++ (with pkgs; [
            gnumake
            taplo
            pandoc
            python3
          ]) ++ pkgs.lib.optionals pkgs.stdenv.isLinux [
            # chromium is only built on Linux in nixpkgs; on macOS users should
            # set LSC_BROWSER to the system Chrome binary, e.g.:
            #   LSC_BROWSER="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" make pdf
            pkgs.chromium
          ];
          shellHook = ''
            echo "lsc dev shell · zola $(zola --version)"
            echo "make dev    — start zola dev server"
            echo "make build  — build static site to site/public"
            echo "make clean  — remove build artifacts"
          '';
        };
      });
}
