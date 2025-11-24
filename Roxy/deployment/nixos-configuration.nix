# NixOS Configuration for Roxy Dog Monitor
# /etc/nixos/configuration.nix

{ config, pkgs, ... }:

{
  imports = [ ./hardware-configuration.nix ];

  # System
  system.stateVersion = "24.05";

  # Bootloader
  boot.loader.grub.enable = true;
  boot.loader.grub.device = "/dev/xvda";

  # Networking
  networking = {
    hostName = "roxy-monitor";
    networkmanager.enable = true;

    # Firewall configuration
    firewall = {
      enable = true;
      allowedTCPPorts = [ 22 ];  # SSH only
      # Uncomment if you need external access to these:
      # allowedTCPPorts = [ 22 8554 8888 ];  # SSH, RTSP, Wyze Bridge Web UI
    };
  };

  # Time zone
  time.timeZone = "America/New_York";

  # Localization
  i18n.defaultLocale = "en_US.UTF-8";

  # User account
  users.users.roxy = {
    isNormalUser = true;
    description = "Roxy Monitor User";
    extraGroups = [ "wheel" "docker" "networkmanager" ];
    openssh.authorizedKeys.keys = [
      # Add your SSH public key here
      # "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC... your-key-here"
    ];
  };

  # Security hardening
  security = {
    sudo = {
      enable = true;
      wheelNeedsPassword = true;
    };

    # Disable root login
    sudo.extraRules = [{
      users = [ "roxy" ];
      commands = [
        { command = "ALL"; options = [ "SETENV" ]; }
      ];
    }];
  };

  # SSH hardening
  services.openssh = {
    enable = true;
    settings = {
      PasswordAuthentication = false;
      PermitRootLogin = "no";
      X11Forwarding = false;
      MaxAuthTries = 3;
      ClientAliveInterval = 300;
      ClientAliveCountMax = 2;
    };
    # Use key-based authentication only
    extraConfig = ''
      AllowUsers roxy
      Protocol 2
    '';
  };

  # Automatic security updates
  system.autoUpgrade = {
    enable = true;
    allowReboot = false;  # Set to true if you want auto-reboots
    dates = "04:00";
  };

  # Docker
  virtualisation.docker = {
    enable = true;
    autoPrune = {
      enable = true;
      dates = "weekly";
    };
  };

  # System packages
  environment.systemPackages = with pkgs; [
    # Essential tools
    vim
    git
    wget
    curl
    htop
    tmux

    # Docker tools
    docker-compose

    # Python for Roxy
    python311
    python311Packages.pip
    python311Packages.virtualenv

    # Network tools
    nettools
    iptables

    # Monitoring
    sysstat
    iotop

    # Security
    fail2ban
  ];

  # Python development environment
  programs.python3 = {
    enable = true;
  };

  # Fail2ban for SSH protection
  services.fail2ban = {
    enable = true;
    maxretry = 3;
    bantime = "1h";
    ignoreIP = [
      "127.0.0.1/8"
      # Add your trusted IPs here
    ];
  };

  # Automatic garbage collection
  nix.gc = {
    automatic = true;
    dates = "weekly";
    options = "--delete-older-than 30d";
  };

  # Enable nix-command and flakes (modern Nix features)
  nix.settings.experimental-features = [ "nix-command" "flakes" ];

  # Systemd service for Roxy Monitor
  systemd.services.roxy-monitor = {
    description = "Roxy Dog Monitor";
    after = [ "network.target" "docker.service" ];
    wants = [ "docker.service" ];
    wantedBy = [ "multi-user.target" ];

    serviceConfig = {
      Type = "simple";
      User = "roxy";
      WorkingDirectory = "/opt/roxy";
      ExecStart = "${pkgs.python311}/bin/python3 /opt/roxy/roxy_monitor.py";
      Restart = "on-failure";
      RestartSec = "30s";

      # Security hardening
      NoNewPrivileges = true;
      PrivateTmp = true;
      ProtectSystem = "strict";
      ProtectHome = true;
      ReadWritePaths = [ "/opt/roxy/alerts" "/opt/roxy/.env" ];

      # Resource limits
      MemoryLimit = "1G";
      CPUQuota = "50%";
    };

    environment = {
      PYTHONUNBUFFERED = "1";
    };
  };

  # Docker Compose service for Wyze Bridge
  systemd.services.wyze-bridge = {
    description = "Wyze Bridge Docker Service";
    after = [ "docker.service" ];
    requires = [ "docker.service" ];
    wantedBy = [ "multi-user.target" ];

    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      WorkingDirectory = "/opt/roxy/deployment";
      ExecStart = "${pkgs.docker-compose}/bin/docker-compose up -d wyze-bridge";
      ExecStop = "${pkgs.docker-compose}/bin/docker-compose down";
      User = "roxy";
    };
  };

  # Monitoring and logging
  services.journald = {
    extraConfig = ''
      SystemMaxUse=500M
      MaxRetentionSec=1month
    '';
  };

  # Optional: CloudWatch agent for AWS monitoring
  # Uncomment if you want AWS CloudWatch integration
  # services.amazon-cloudwatch-agent.enable = true;
}
