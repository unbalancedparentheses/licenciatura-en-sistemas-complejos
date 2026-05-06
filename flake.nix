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
      in {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            zola
            gnumake
            taplo
            pandoc
            python3
          ] ++ pkgs.lib.optionals pkgs.stdenv.isLinux [
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
