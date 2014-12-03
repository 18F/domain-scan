#!/usr/bin/env ruby

require 'rubygems'
require 'csv'
require 'site-inspector'
require 'oj'

FileUtils.mkdir_p "cache"

INPUT_CSV = ARGV[0] || "domains.csv"

def go
  CSV.open("output.csv", "w") do |analysis|

    analysis << [
      "Domain",
      "Details",
      "Entity",
      "HTTPS?",
      "Force HTTPS?",
      "HSTS?",
      "HSTS Header"
    ]

    CSV.foreach(INPUT_CSV) do |row|
      next if row[0].strip.downcase == "domain name"
      domain = row[0].strip.downcase

      from_csv = {
        'domain' => domain,
        'details' => row[1].strip,
        'entity' => (row[2] ? row[2].strip : nil)
      }

      puts "[#{from_csv['domain']}]"

      puts "\t[#{from_csv['domain']}]"
      from_domain = check_domain from_csv
      analysis << [
        from_csv['domain'],
        from_csv['details'],
        from_csv['entity'],
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

def uncache!(domain)
  if File.exists?(cache_path(domain))
    Oj.load(File.read(cache_path(domain)))
  end
end

def check_domain(from_csv)
  domain = from_csv['domain']

  from_domain = uncache!(domain)

  if from_domain
    puts "\tCached, skipping."

  else
    begin
      site = SiteInspector.new domain
    rescue Exception => exc
      puts "\tERROR."
      puts exc
      return []
    end

    # TODO: send looser strict check upstream
    hsts = nil
    if site.response
      strict_header = site.response.headers.keys.find {|h| h.downcase =~ /^strict/}
      if strict_header
        hsts = site.response.headers[strict_header]
      end
    end

    from_domain = {
      'site' => domain_details(site),
      'derived' => {
        'hsts' => !!hsts,
        'hsts_header' => hsts
      },
      'headers' => site.response.headers
    }

    cache! from_domain, domain
    puts "\tFetched, cached."
    # normalize to be read from cache again
    from_domain = uncache!(domain)
  end

  {
    'domain' => domain,
    'https' => from_domain['site']['ssl'],
    'force_https' => from_domain['site']['enforce_https'],
    'hsts' => from_domain['derived']['hsts'],
    'hsts_header' => from_domain['derived']['hsts_header']
  }
end

# what fields from site-inspector do we care about
def domain_details(site)
  {
    'live' => !!(site.response),
    'ssl' => site.https?,
    'enforce_https' => site.enforce_https?,
    'non_www' => site.non_www?,
    'redirect' => site.redirect,
    'click_jacking_protection' => site.click_jacking_protection?,
    'content_security_policy' => site.content_security_policy?,
    'xss_protection' => site.xss_protection?,
    'secure_cookies' => site.secure_cookies?,
    'strict_transport_security' => site.strict_transport_security?
  }
end

# go
go
