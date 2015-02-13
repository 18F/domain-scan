#!/usr/bin/env ruby

require 'rubygems'
require 'bundler/setup'

require 'csv'
require 'site-inspector'
require 'oj'

FileUtils.mkdir_p "cache"

INPUT_CSV = ARGV[0] || "domains.csv"

DEBUG_DOMAIN = ARGV[1]

def go
  CSV.open("output.csv", "w") do |analysis|

    analysis << [
      "Domain",
      "Details",
      "Entity",
      "Live?",
      "Redirect?",
      "HTTPS?",
      "Force HTTPS?",
      "HSTS?",
      "HSTS Header"
    ]

    if DEBUG_DOMAIN
      domains = [[DEBUG_DOMAIN, nil, nil]]
    else
      domains = CSV.read(INPUT_CSV)
    end

    domains.each do |row|
      next if row[0].strip.downcase == "domain name"
      domain = row[0].strip.downcase

      # will need to change for .mil
      next unless domain.end_with?(".gov")

      from_csv = {
        'domain' => domain,
        'details' => (row[1] ? row[1].strip : nil),
        'entity' => (row[2] ? row[2].strip : nil)
      }

      puts "[#{from_csv['domain']}]"

      puts "\t[#{from_csv['domain']}]"
      from_domain = check_domain domain
      analysis << [
        from_csv['domain'],
        from_csv['details'],
        from_csv['entity'],
        from_domain['live'],
        from_domain['redirect'],
        from_domain['https'],
        from_domain['force_https'],
        from_domain['hsts'],
        from_domain['hsts_header']
      ]
    end

  end

end

def cache_path(domain)
  "cache/#{domain}.json"
end

def cache!(response, domain)
  File.open(cache_path(domain), "w") {|f| f.write Oj.dump(response, indent: 2, mode: :compat)}
end

def from_cache!(domain)
  if File.exists?(cache_path(domain))
    Oj.load(File.read(cache_path(domain)))
  end
end

def check_domain(domain)

  from_domain = from_cache!(domain)

  if from_domain
    puts "\tCached, skipping."

  else
    begin
      open("https://18f.gsa.gov").read
      site = SiteInspector.new domain

    rescue SocketError, Exception => exc
      puts "\tERROR."
      puts exc
      return {}
    end

    from_domain = {
      'site' => domain_details(site),
      'headers' => (site.response ? site.response.headers : nil)
    }

    cache! from_domain, domain
    puts "\tFetched, cached."
    # normalize to be read from cache again
    from_domain = from_cache!(domain)
  end

  {
    'domain' => domain,
    'live' => from_domain['site']['live'],
    'redirect' => from_domain['site']['redirect'],
    'https' => from_domain['site']['ssl'],
    'force_https' => from_domain['site']['enforce_https'],
    'hsts' => from_domain['site']['strict_transport_security'],
    'hsts_header' => from_domain['site']['strict_transport_security_details']
  }
end

# what fields from site-inspector do we care about
def domain_details(site)
  {
    # basic domain facts
    'live' => !!(site.response),
    'non_www' => site.non_www?,
    'redirect' => site.redirect,

    # HTTPS presence and quality
    'ssl' => site.https?,
    'enforce_https' => site.enforce_https?,
    'strict_transport_security' => site.strict_transport_security?,
    'strict_transport_security_details' => site.strict_transport_security,

    # other security features
    'click_jacking_protection' => site.click_jacking_protection?,
    'click_jacking_protection_details' => site.click_jacking_protection,
    'content_security_policy' => site.content_security_policy?,
    'content_security_policy_details' => site.content_security_policy,
    'xss_protection' => site.xss_protection?,
    'xss_protection_details' => site.xss_protection,
    'secure_cookies' => site.secure_cookies?
  }
end

# go
go
