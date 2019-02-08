<#
.SYNOPSIS
    Run Datera PoC checks to determine fitness for communicating with a Datera cluster
.DESCRIPTION
    This script will run through the following checks to determine if it is ready
    for use with a Datera cluster.
        * ISCSI services check
        * Management connection check
        * VIP1 connection check
        * VIP2 connection check
        * Management mtu check
        * VIP1 mtu check
        * VIP2 mtu check
        * Power settings check
        * Receive side scaling check
.EXAMPLE
    Copy this file to the Desktop of the Admin account
    Ensure the Datera powershell-sdk is installed
    (SEE: https://github.com/Datera/powershell-sdk) and a valid Universal
    Datera Config file is available with the connection credentials to the
    desired Datera DSP cluster.

    Run
    C:\Users\Admin\Desktop\check_windows.ps1 -human
    --------------
    Example Output
    --------------
    Checking ISCSI Service
    SUCCESS
    Testing vip_1 Connection
    SUCCESS
    Testing vip_2 Connection
    SUCCESS
    Testing mgmt_ip Connection
    SUCCESS
    vip_2 was not populated, skipping MTU test
    Testing vip_1 MTU
    SUCCESS
    Testing mgmt_ip MTU
    SUCCESS
    Checking Power Settings
    Power settings are not set to 'High performance'
    Checking Recieve Side Scaling
    SUCCESS
    Finished.  Status Code: 256
    FAILED_POWER_SETTINGS

    Each check will either report SUCCESS or it will display an error at the end
    of the test run.
#>
Using module dsdk

Param(
    [Parameter(Mandatory=$false)]
    [switch]$human = $false
)

Set-StrictMode -Version Latest

$EXITCODE = 0

[Flags()] enum Failures {
    FAILED_ISCSI_SERVICE    = 1
    FAILED_CONNECTION_MGMT  = 2
    FAILED_CONNECTION_VIP1  = 4
    FAILED_CONNECTION_VIP2  = 8
    FAILED_MTU_MGMT         = 16
    FAILED_MTU_VIP1         = 32
    FAILED_MTU_VIP2         = 64
    FAILED_POWER_SETTINGS   = 128
    FAILED_RSS              = 256
}

function Add-Error {
    Param([Parameter(Mandatory=$true)] [Failures]$error_code)
    $script:EXITCODE += $error_code
}

function Write-Human {
    Param([Parameter(Mandatory=$true)] [string]$output)
    If ($human) {
        Write-Output $output
    }
}

$cfg = Get-UdcConfig
$ips = @($cfg.mgmt_ip)

# Get the Datera VIPs
$sys = Get-DateraSystem
$vip1 = $sys |
        Select-Object -ExpandProperty network |
        Select-Object -ExpandProperty access_vip |
        Select-Object -ExpandProperty network_paths |
        Select-Object -Index 0 |
        Select-Object -ExpandProperty ip

$vip2 = $sys |
        Select-Object -ExpandProperty network |
        Select-Object -ExpandProperty access_vip |
        Select-Object -ExpandProperty network_paths |
        Select-Object -Index 1 |
        Select-Object -ExpandProperty ip
$cfg | Add-Member "vip_1" $vip1 -PassThru
$cfg | Add-Member "vip_2" $vip2 -PassThru

# Check Connections
$conn_errs = @{
    "mgmt_ip" = [Failures]::FAILED_CONNECTION_MGMT;
    "vip_1" = [Failures]::FAILED_CONNECTION_VIP1;
    "vip_2" = [Failures]::FAILED_CONNECTION_VIP2
}

Function Test-Ip {
    Param(
        [Parameter(mandatory=$true)]
        [string]$name,

        [Parameter(mandatory=$true)]
        [string]$ip
    )
    If ($ip -eq "") {
        Write-Human "$name was not populated, skipping connection test"
        continue
    }
    Write-Human "Testing $name Connection"
    If (!(Test-Connection -Cn $ip -BufferSize 16 -Count 1 -ea 0 -quiet)) {
        Write-Human "FAIL: Could not reach $ip, please check the connection"
        Add-Error $conn_errs[$name]
    } Else {
        Write-Human "SUCCESS"
    }

}

Foreach ($k in $conn_errs.keys) {
    Test-Ip $k $cfg."$k"
}

# Check MTU
$mtu = 9000
$mtu_errs = @{"mgmt_ip" = [Failures]::FAILED_MTU_MGMT;
              "vip_1" = [Failures]::FAILED_MTU_VIP1;
              "vip_2" = [Failures]::FAILED_MTU_VIP2}
Foreach ($k in $conn_errs.keys) {
    If ($cfg."$k" -eq "") {
        Write-Human "$k was not populated, skipping MTU test"
        continue
    }
    Write-Human "Testing $k MTU"
    If (!(ping $cfg."$k" -f -l $mtu)) {
        Write-Human "Could not reach $($cfg.`"$k`"), with MTU of $mtu, please check MTU settings"
        Add-Error $mtu_errs[$k]
    } Else {
        Write-Human "SUCCESS"
    }
}

# Check ISCSI service
Write-Human "Checking ISCSI Service"
$iscsi_enabled = (Get-Service MSiSCSI).Status -eq "Running"
If (!$iscsi_enabled) {
    Write-Human "FAIL: The MSiSCSI service is not running"
    Add-Error ([Failures]::FAILED_ISCSI_SERVICE)
} Else {
    Write-Human "SUCCESS"
}

# Check Power Settings
Write-Human "Checking Power Settings"
If (!(powercfg -l | Where-Object {$_.contains("High performance")} | Foreach-Object {$_.contains("*")})) {
    Write-Human("Power settings are not set to 'High performance'")
    Add-Error ([Failures]::FAILED_POWER_SETTINGS)
}

# Check Receive Side Scaling
Write-Human "Checking Recieve Side Scaling"
$rssm = Get-NetAdapterRss * | Where-Object {$_.Enabled -eq $false} | Measure-Object
If ($rssm.Count -ne 0) {
    Get-NetAdapterRss * | Where-Object {$_.Enabled -eq $false} | Foreach-Object {
            Write-Human "Interface $_.Name does not have Receive Side Scaling enabled"
        }
    Add-Error ([Failures]::FAILED_RSS)
} Else {
    Write-Human "SUCCESS"
}

Write-Human("Finished.  Status Code: $EXITCODE")
If ($human) {
    Write-Human [Failures]$EXITCODE
}
exit $EXITCODE
